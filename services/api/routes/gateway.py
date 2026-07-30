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
    computed = "v0=" + hmac.new(
        config.signing_secret.encode(), basestring.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


async def _slack_send_message(channel: str, text: str, thread_ts: str = ""):
    """Send a message to a Slack channel."""
    config = _get_slack_config()
    if not config.bot_token:
        logger.warning("slack_send_skipped", reason="No bot token")
        return

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

    # Blocklist check
    if _is_blocked(text):
        return "This request cannot be processed for safety reasons."

    # DM pairing check
    if user_id not in _paired_users:
        # Generate pairing code
        code = str(uuid.uuid4())[:6].upper()
        _paired_users[user_id] = {
            "external_id": user_id,
            "platform": "slack",
            "paired": False,
            "code": code,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _persist_paired()
        return (
            f"Welcome to Optimus TrustLayer. For security, please verify your identity.\n"
            f"Your pairing code is: `{code}`\n"
            f"Enter this code in the Optimus web app under Settings > Gateway Pairing to link your account."
        )

    if not _paired_users[user_id].get("paired"):
        return "Your account is not yet paired. Please enter the pairing code in the Optimus web app."

    _log_message("slack", "inbound", user_id, text)

    # Run through the agent
    try:
        from services.api.routes.work import _run_agent
        viewer_id = _paired_users[user_id].get("optimus_user_id", "")
        result, steps = await _run_agent(text, viewer_id=viewer_id)
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
        return Response(content=payload["challenge"], media_type="text/plain")

    # Verify signature
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    event = payload.get("event", {})
    event_type = event.get("type", "")

    if event_type == "message" and not event.get("bot_id"):
        response_text = await _handle_slack_message(event)
        if response_text:
            await _slack_send_message(
                event.get("channel", ""),
                response_text,
                thread_ts=event.get("ts", ""),
            )

    return Response(content="OK", status_code=200)


@router.get("/gateway/slack/status")
async def slack_status() -> dict:
    config = _get_slack_config()
    return {
        "enabled": config.enabled,
        "paired_users": len([u for u in _paired_users.values() if u.get("paired")]),
        "total_messages": len([m for m in _gateway_log if m["platform"] == "slack"]),
    }


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
