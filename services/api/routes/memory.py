"""Persistent memory system — remembers facts, preferences, and learnings across chats."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from libs.config.settings import get_settings
from libs.observability.logging import get_logger

logger = get_logger("memory")

router = APIRouter()


class Memory(BaseModel):
    id: str
    content: str
    category: str  # "fact" | "preference" | "learning" | "entity_note"
    source: str  # "user" | "system" | "conversation"
    created_at: str
    relevance_score: float = 1.0
    metadata: dict[str, Any] = {}


class MemoryStore(BaseModel):
    memories: list[Memory]
    total: int


# Per-user memory store (production: Postgres)
_memory_store: dict[str, list[Memory]] = {}

MEMORY_FILE = "data/memories.json"


def _load_from_disk() -> dict[str, list[Memory]]:
    """Load memories from disk for persistence across restarts."""
    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
            result: dict[str, list[Memory]] = {}
            for user_id, mems in data.items():
                result[user_id] = [Memory(**m) for m in mems]
            return result
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_to_disk():
    """Persist memories to disk."""
    import os

    os.makedirs("data", exist_ok=True)
    data = {}
    for user_id, mems in _memory_store.items():
        data[user_id] = [m.model_dump() for m in mems]
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


# Load on module init
_memory_store = _load_from_disk()


def get_memories(user_id: str, limit: int = 20) -> list[Memory]:
    """Get recent memories for a user."""
    mems = _memory_store.get(user_id, [])
    return sorted(mems, key=lambda m: m.created_at, reverse=True)[:limit]


def add_memory(user_id: str, content: str, category: str, source: str = "system", metadata: dict | None = None) -> Memory:
    """Add a memory for a user."""
    if user_id not in _memory_store:
        _memory_store[user_id] = []

    # Dedup: don't store if identical content already exists
    for existing in _memory_store[user_id]:
        if existing.content.lower().strip() == content.lower().strip():
            return existing

    mem = Memory(
        id=str(uuid.uuid4()),
        content=content,
        category=category,
        source=source,
        created_at=datetime.utcnow().isoformat(),
        metadata=metadata or {},
    )
    _memory_store[user_id].append(mem)

    # Cap at 500 memories per user
    if len(_memory_store[user_id]) > 500:
        _memory_store[user_id] = _memory_store[user_id][-500:]

    _save_to_disk()
    return mem


async def extract_memories_from_conversation(
    user_id: str, question: str, answer: str
):
    """Use LLM to extract memorable facts from a conversation turn."""
    settings = get_settings()
    openai_key = settings.openai_api_key.get_secret_value()
    portkey_key = settings.portkey_api_key.get_secret_value()

    if not openai_key:
        return

    headers: dict[str, str] = {"Content-Type": "application/json"}
    base_url = "https://api.openai.com/v1"

    headers["Authorization"] = f"Bearer {openai_key}"

    extraction_prompt = (
        "Extract any memorable facts, user preferences, or important information "
        "from this conversation that would be useful to remember for future chats. "
        "Return a JSON array of objects with 'content' (the fact) and 'category' "
        "(one of: fact, preference, learning, entity_note). "
        "Only extract genuinely useful information. If nothing is worth remembering, "
        "return an empty array []. Be selective — quality over quantity.\n\n"
        f"User: {question}\n"
        f"Assistant: {answer[:500]}"
    )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You extract memorable facts from conversations. Return valid JSON only."},
                        {"role": "user", "content": extraction_prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500,
                    "response_format": {"type": "json_object"},
                },
                timeout=15.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                items = parsed.get("memories", parsed) if isinstance(parsed, dict) else parsed
                if isinstance(items, list):
                    for item in items[:3]:
                        if isinstance(item, dict) and item.get("content"):
                            add_memory(
                                user_id,
                                item["content"],
                                item.get("category", "fact"),
                                source="conversation",
                            )
    except Exception as e:
        logger.warning("memory_extraction_failed", error=str(e))


@router.get("/memory", response_model=MemoryStore)
async def list_memories(user_id: str = "default") -> MemoryStore:
    mems = get_memories(user_id, limit=50)
    return MemoryStore(memories=mems, total=len(mems))


@router.post("/memory")
async def create_memory(
    content: str, category: str = "fact", user_id: str = "default"
) -> Memory:
    return add_memory(user_id, content, category, source="user")


@router.delete("/memory/{memory_id}")
async def delete_memory(memory_id: str, user_id: str = "default") -> dict:
    if user_id in _memory_store:
        _memory_store[user_id] = [
            m for m in _memory_store[user_id] if m.id != memory_id
        ]
        _save_to_disk()
    return {"deleted": memory_id}


@router.delete("/memory")
async def clear_memories(user_id: str = "default") -> dict:
    count = len(_memory_store.get(user_id, []))
    _memory_store[user_id] = []
    _save_to_disk()
    return {"cleared": count}


# ═══════════════════════════════════════════════════════════════════════
# Server-side chat history persistence
# ═══════════════════════════════════════════════════════════════════════

CHATS_FILE = "data/chat_history.json"

_chat_store: dict[str, list[dict]] = {}

def _load_chats():
    global _chat_store
    try:
        with open(CHATS_FILE, "r") as f:
            _chat_store = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _chat_store = {}

def _save_chats():
    import os
    os.makedirs("data", exist_ok=True)
    with open(CHATS_FILE, "w") as f:
        json.dump(_chat_store, f)

_load_chats()


@router.get("/chats")
async def list_chats(user_id: str = "default") -> list[dict]:
    sessions = _chat_store.get(user_id, [])
    return sorted(sessions, key=lambda s: s.get("updatedAt", 0), reverse=True)


class ChatSyncRequest(BaseModel):
    user_id: str = "default"
    sessions: list[dict] = []


@router.post("/chats")
async def save_chats(req: ChatSyncRequest) -> dict:
    _chat_store[req.user_id] = req.sessions
    _save_chats()
    return {"saved": len(req.sessions)}
