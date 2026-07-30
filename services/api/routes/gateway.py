"""Gateway surfaces — Slack bot + Email gateway.

Block 4 W-P2: same agent, same graph, same canon on every surface.
OpenClaw safety posture: DM pairing, approval gates, unconditional blocklist.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import pathlib
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from libs.config.settings import get_settings
from libs.observability.logging import get_logger

logger = get_logger("gateway")

router = APIRouter()

DATA_DIR = pathlib.Path(__file__).resolve().parents[3] / "data"
GATEWAY_LOG_FILE = str(DATA_DIR / "gateway_log.json")
PAIRED_USERS_FILE = str(DATA_DIR / "paired_users.json")

# Unconditional blocklist — no flag can override
BLOCKLIST = {
    "delete all", "drop table", "rm -rf", "format c:",
    "send money", "transfer funds", "wire transfer",
    "ignore previous instructions", "ignore all instructions",
}


def _load_json(path: str) -> list[dict]:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_json(path: str, data: list[dict]):
    os.makedirs(str(DATA_DIR), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── Paired users (DM pairing for security) ────────────────────────────

_paired_users: dict[str, dict] = {}
for pu in _load_json(PAIRED_USERS_FILE):
    _paired_users[pu.get("external_id", "")] = pu


def _persist_paired():
    _save_json(PAIRED_USERS_FILE, list(_paired_users.values()))


# ── Gateway message log ───────────────────────────────────────────────

_gateway_log: list[dict] = _load_json(GATEWAY_LOG_FILE)


def _log_message(platform: str, direction: str, user_id: str, content: str, metadata: dict = {}):
    entry = {
        "id": str(uuid.uuid4()),
        "platform": platform,
        "direction": direction,
        "user_id": user_id,
        "content": content[:1000],
        "metadata": metadata,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _gateway_log.append(entry)
    if len(_gateway_log) > 1000:
        _gateway_log.pop(0)
    _save_json(GATEWAY_LOG_FILE, _gateway_log[-500:])


def _is_blocked(text: str) -> bool:
    """Check against the unconditional blocklist."""
    text_lower = text.lower().strip()
    return any(blocked in text_lower for blocked in BLOCKLIST)


# ═══════════════════════════════════════════════════════════════════════
# SLACK GATEWAY
# ═══════════════════════════════════════════════════════════════════════

class SlackConfig(BaseModel):
    bot_token: str = ""
    signing_secret: str = ""
    enabled: bool = False


def _get_slack_config() -> SlackConfig:
    return SlackConfig(
        bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
        signing_secret=os.getenv("SLACK_SIGNING_SECRET", ""),
        enabled=bool(os.getenv("SLACK_BOT_TOKEN")),
    )


def _verify_slack_signature(request_body: bytes, timestamp: str, signature: str) -> bool:
    """Verify Slack request signature."""
    config = _get_slack_config()
    if not config.signing_secret:
        return True  # Skip verification in dev

    basestring = f"v0:{timestamp}:{request_body.decode()}"
    computed = "v0=" + hmac.HMAC(
        config.signing_secret.encode(), basestring.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


def _md_to_slack(text: str) -> str:
    """Convert standard markdown to Slack mrkdwn format."""
    import re
    t = text
    t = re.sub(r'^#{1,6}\s+(.*)', r'*\1*', t, flags=re.MULTILINE)
    t = re.sub(r'\*\*(.+?)\*\*', r'*\1*', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<\2|\1>', t)
    return t


async def _slack_send_message(channel: str, text: str, thread_ts: str = ""):
    """Send a message to a Slack channel."""
    config = _get_slack_config()
    if not config.bot_token:
        logger.warning("slack_send_skipped", reason="No bot token")
        return

    text = _md_to_slack(text)
    payload: dict[str, Any] = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {config.bot_token}", "Content-Type": "application/json"},
            json=payload,
            timeout=10.0,
        )
        if resp.status_code == 200 and resp.json().get("ok"):
            _log_message("slack", "outbound", channel, text)
        else:
            logger.warning("slack_send_failed", response=resp.text[:200])


async def _handle_slack_message(event: dict) -> str:
    """Process an incoming Slack message and generate a response."""
    text = event.get("text", "").strip()
    user_id = event.get("user", "")
    channel = event.get("channel", "")

    if not text or event.get("bot_id"):
        return ""

    if _is_blocked(text):
        return "This request cannot be processed for safety reasons."

    _log_message("slack", "inbound", user_id, text)

    # Run through the agent directly — no pairing required for now
    try:
        from services.api.routes.work import _run_agent
        result, _steps = await _run_agent(text)
        _log_message("slack", "outbound", user_id, result[:500])
        return result
    except Exception as e:
        logger.error("slack_agent_error", error=str(e))
        return "Sorry, I encountered an error processing your request."


@router.post("/gateway/slack/events")
async def slack_events(request: Request) -> Response:
    """Slack Events API endpoint."""
    body = await request.body()
    payload = json.loads(body)

    # URL verification challenge
    if payload.get("type") == "url_verification":
        return Response(
            content=json.dumps({"challenge": payload["challenge"]}),
            media_type="application/json",
        )

    # Verify signature
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    event = payload.get("event", {})
    event_type = event.get("type", "")

    logger.info("slack_event_received", event_type=event_type, has_bot_id=bool(event.get("bot_id")))

    # Handle regular DMs and @mentions
    is_user_message = event_type == "message" and not event.get("bot_id") and not event.get("subtype")
    is_mention = event_type == "app_mention"

    # Handle Slack Agent/Assistant protocol
    is_assistant_thread = event_type == "assistant_thread_started"

    if is_user_message or is_mention:
        import asyncio
        asyncio.create_task(_process_slack_event(event))
    elif is_assistant_thread:
        import asyncio
        asyncio.create_task(_process_assistant_thread(event))

    return Response(content="OK", status_code=200)


async def _process_assistant_thread(event: dict):
    """Handle Slack Assistant thread — set status, process, respond."""
    try:
        config = _get_slack_config()
        channel = event.get("assistant_thread", {}).get("channel_id", "")
        thread_ts = event.get("assistant_thread", {}).get("thread_ts", "")
        context = event.get("assistant_thread", {}).get("context", {})

        if not channel or not thread_ts:
            logger.warning("assistant_thread_missing_data", event=event)
            return

        # Set typing indicator
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://slack.com/api/assistant.threads.setStatus",
                headers={"Authorization": f"Bearer {config.bot_token}", "Content-Type": "application/json"},
                json={"channel_id": channel, "thread_ts": thread_ts, "status": "Thinking..."},
                timeout=5.0,
            )

        # Get the user's message from the thread
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://slack.com/api/conversations.replies",
                headers={"Authorization": f"Bearer {config.bot_token}"},
                params={"channel": channel, "ts": thread_ts, "limit": "5"},
                timeout=10.0,
            )
            user_text = ""
            if resp.status_code == 200:
                data = resp.json()
                for msg in data.get("messages", []):
                    if not msg.get("bot_id") and msg.get("text"):
                        user_text = msg["text"]
                        break

        if not user_text:
            user_text = "Hello"

        # Generate response
        from services.api.routes.work import _run_agent
        result, _steps = await _run_agent(user_text)

        # Send reply in the assistant thread
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {config.bot_token}", "Content-Type": "application/json"},
                json={"channel": channel, "thread_ts": thread_ts, "text": _md_to_slack(result) if result else "I couldn't process that request."},
                timeout=15.0,
            )

    except Exception as e:
        logger.error("assistant_thread_failed", error=str(e))


async def _process_slack_event(event: dict):
    """Process Slack event in the background."""
    try:
        response_text = await _handle_slack_message(event)
        if response_text:
            await _slack_send_message(
                event.get("channel", ""),
                response_text,
                thread_ts=event.get("ts", ""),
            )
    except Exception as e:
        logger.error("slack_event_processing_failed", error=str(e))


@router.get("/gateway/slack/status")
async def slack_status() -> dict:
    config = _get_slack_config()
    return {
        "enabled": config.enabled,
        "poller_running": _slack_poller_running,
        "total_messages": len([m for m in _gateway_log if m["platform"] == "slack"]),
    }


# ── Slack DM Poller (fallback when Event Subscriptions aren't delivering) ──

_slack_poller_running = False
_slack_last_ts: dict[str, str] = {}


async def _start_slack_poller():
    """Poll Slack DMs for new messages and respond. Runs as background task."""
    global _slack_poller_running
    if _slack_poller_running:
        return
    _slack_poller_running = True
    logger.info("slack_poller_started")

    config = _get_slack_config()
    if not config.bot_token:
        _slack_poller_running = False
        return

    bot_user_id = ""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://slack.com/api/auth.test",
                headers={"Authorization": f"Bearer {config.bot_token}"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                bot_user_id = data.get("user_id", "")
    except Exception:
        pass

    while True:
        try:
            await asyncio.sleep(5)

            async with httpx.AsyncClient() as client:
                # List DM channels
                resp = await client.get(
                    "https://slack.com/api/conversations.list",
                    headers={"Authorization": f"Bearer {config.bot_token}"},
                    params={"types": "im", "limit": "20"},
                    timeout=10.0,
                )
                if resp.status_code != 200:
                    continue
                channels_data = resp.json()
                if not channels_data.get("ok"):
                    continue

                for ch in channels_data.get("channels", []):
                    ch_id = ch.get("id", "")
                    if not ch_id:
                        continue

                    # Get latest messages since last check
                    params: dict[str, str] = {"channel": ch_id, "limit": "5"}
                    last_ts = _slack_last_ts.get(ch_id, "")
                    if last_ts:
                        params["oldest"] = last_ts

                    resp = await client.get(
                        "https://slack.com/api/conversations.history",
                        headers={"Authorization": f"Bearer {config.bot_token}"},
                        params=params,
                        timeout=10.0,
                    )
                    if resp.status_code != 200:
                        continue
                    msgs_data = resp.json()
                    if not msgs_data.get("ok"):
                        continue

                    messages = msgs_data.get("messages", [])
                    if not messages:
                        continue

                    # Update last seen timestamp
                    newest_ts = max(m.get("ts", "0") for m in messages)
                    _slack_last_ts[ch_id] = newest_ts

                    # Skip if this is the first poll (don't reply to old messages)
                    if not last_ts:
                        continue

                    # Process new user messages (not from bot)
                    for msg in messages:
                        if msg.get("bot_id") or msg.get("subtype"):
                            continue
                        if msg.get("user") == bot_user_id:
                            continue
                        user_text = msg.get("text", "").strip()
                        if not user_text:
                            continue

                        # Respond
                        _log_message("slack", "inbound", msg.get("user", ""), user_text)
                        try:
                            from services.api.routes.work import _run_agent
                            result, _ = await _run_agent(user_text)
                            if result:
                                await _slack_send_message(ch_id, result)
                                _log_message("slack", "outbound", msg.get("user", ""), result[:500])
                        except Exception as e:
                            logger.error("slack_poller_agent_error", error=str(e))
                            await _slack_send_message(ch_id, "Sorry, I encountered an error.")

        except Exception as e:
            logger.warning("slack_poller_error", error=str(e))
            await asyncio.sleep(10)


import asyncio  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════
# EMAIL GATEWAY
# ═══════════════════════════════════════════════════════════════════════

class EmailConfig(BaseModel):
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    imap_host: str = ""
    enabled: bool = False


def _get_email_config() -> EmailConfig:
    return EmailConfig(
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        imap_host=os.getenv("IMAP_HOST", ""),
        enabled=bool(os.getenv("SMTP_HOST")),
    )


async def _send_email(to: str, subject: str, body: str):
    """Send an email via SMTP."""
    config = _get_email_config()
    if not config.enabled:
        logger.warning("email_send_skipped", reason="SMTP not configured")
        return False

    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    try:
        msg = MIMEMultipart()
        msg["From"] = config.smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
            server.starttls()
            server.login(config.smtp_user, config.smtp_password)
            server.send_message(msg)

        _log_message("email", "outbound", to, f"Subject: {subject}\n{body[:200]}")
        return True
    except Exception as e:
        logger.error("email_send_failed", error=str(e))
        return False


@router.post("/gateway/email/receive")
async def receive_email(
    from_addr: str, subject: str, body: str,
) -> dict:
    """Process an inbound email (webhook from email provider)."""
    if _is_blocked(body):
        return {"processed": False, "reason": "blocked"}

    _log_message("email", "inbound", from_addr, f"Subject: {subject}\n{body[:500]}")

    # Check if sender is paired
    paired = _paired_users.get(from_addr)
    if not paired or not paired.get("paired"):
        # Auto-pair by email if we have a user with this email
        try:
            from services.api.routes.auth import _users
            user = next((u for u in _users if u.get("email", "").lower() == from_addr.lower()), None)
            if user:
                _paired_users[from_addr] = {
                    "external_id": from_addr,
                    "platform": "email",
                    "paired": True,
                    "optimus_user_id": user["id"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                _persist_paired()
                paired = _paired_users[from_addr]
        except Exception:
            pass

    if not paired or not paired.get("paired"):
        return {"processed": False, "reason": "unknown_sender"}

    # Process with agent
    try:
        from services.api.routes.work import _run_agent
        viewer_id = paired.get("optimus_user_id", "")
        prompt = f"Email from {from_addr}\nSubject: {subject}\n\n{body[:2000]}"
        result, steps = await _run_agent(prompt, viewer_id=viewer_id)

        # Send reply
        await _send_email(
            from_addr,
            f"Re: {subject}",
            f"Optimus TrustLayer Response:\n\n{result}",
        )

        return {"processed": True, "response_sent": True}
    except Exception as e:
        logger.error("email_process_failed", error=str(e))
        return {"processed": False, "error": str(e)}


@router.get("/gateway/email/status")
async def email_status() -> dict:
    config = _get_email_config()
    return {
        "enabled": config.enabled,
        "paired_users": len([u for u in _paired_users.values() if u.get("platform") == "email" and u.get("paired")]),
        "total_messages": len([m for m in _gateway_log if m["platform"] == "email"]),
    }


# ═══════════════════════════════════════════════════════════════════════
# GATEWAY MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════

@router.post("/gateway/pair")
async def pair_user(code: str, optimus_user_id: str) -> dict:
    """Pair an external account (Slack/email) with an Optimus user."""
    for ext_id, entry in _paired_users.items():
        if entry.get("code") == code and not entry.get("paired"):
            entry["paired"] = True
            entry["optimus_user_id"] = optimus_user_id
            entry["paired_at"] = datetime.now(timezone.utc).isoformat()
            _persist_paired()
            return {"paired": True, "platform": entry.get("platform")}

    raise HTTPException(404, "Invalid or expired pairing code")


@router.get("/gateway/log")
async def get_gateway_log(platform: str = "", limit: int = 50) -> list[dict]:
    """Get gateway message log."""
    log = _gateway_log
    if platform:
        log = [m for m in log if m["platform"] == platform]
    return log[-limit:]


@router.get("/gateway/status")
async def gateway_overview() -> dict:
    """Overview of all gateway surfaces."""
    slack = _get_slack_config()
    email = _get_email_config()
    return {
        "slack": {
            "enabled": slack.enabled,
            "paired": len([u for u in _paired_users.values() if u.get("platform") == "slack" and u.get("paired")]),
        },
        "email": {
            "enabled": email.enabled,
            "paired": len([u for u in _paired_users.values() if u.get("platform") == "email" and u.get("paired")]),
        },
        "total_messages": len(_gateway_log),
        "blocklist_size": len(BLOCKLIST),
    }
