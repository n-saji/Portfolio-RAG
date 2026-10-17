"""Bounded, session-scoped conversation memory for the LangGraph agent."""

import json
import os
import uuid

import redis
from dotenv import load_dotenv

load_dotenv()

USE_REDIS = os.getenv("USE_REDIS_MEMORY", "false").lower() == "true"
MAX_MESSAGES = 20
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
redis_client = (
    redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        socket_connect_timeout=2,
        socket_timeout=2,
        decode_responses=True,
    )
    if USE_REDIS
    else None
)


def create_session_id() -> str:
    return str(uuid.uuid4())


def valid_session_id(value: str | None) -> bool:
    if not value:
        return False
    try:
        return str(uuid.UUID(value)) == value.lower()
    except ValueError:
        return False


def _key(session_id: str) -> str:
    return f"session:{session_id}"


def get_chat_messages(session_id: str | None) -> list[dict[str, str]]:
    """Return a safe display transcript, including legacy Redis entries."""
    if not redis_client or not valid_session_id(session_id):
        return []
    try:
        entries = redis_client.lrange(_key(session_id), -MAX_MESSAGES, -1)
    except redis.RedisError:
        return []
    messages = []
    for entry in entries:
        try:
            parsed = json.loads(entry)
            role, content = parsed.get("role"), parsed.get("content")
        except (ValueError, TypeError, AttributeError):
            role, _, content = entry.partition(": ")
            role = {"User": "user", "AI": "assistant"}.get(role)
        if role in {"user", "assistant"} and isinstance(content, str) and content:
            messages.append({"role": role, "content": content[:4000]})
    return messages


def get_chat_history(session_id: str | None) -> str:
    messages = get_chat_messages(session_id)
    return "\n".join(
        f"{'User' if item['role'] == 'user' else 'Assistant'}: {item['content']}"
        for item in messages[-8:]
    )


def save_exchange(session_id: str | None, human_query: str, ai_response: str) -> None:
    if not redis_client or not valid_session_id(session_id):
        return
    key = _key(session_id)
    try:
        with redis_client.pipeline(transaction=True) as pipe:
            pipe.rpush(key, json.dumps({"role": "user", "content": human_query[:500]}))
            pipe.rpush(key, json.dumps({"role": "assistant", "content": ai_response[:4000]}))
            pipe.ltrim(key, -MAX_MESSAGES, -1)
            pipe.expire(key, SESSION_TTL_SECONDS)
            pipe.execute()
    except redis.RedisError:
        # Memory is optional; the answer should still be delivered.
        return


def clear_session_history(session_id: str | None) -> None:
    if not redis_client or not valid_session_id(session_id):
        return
    try:
        redis_client.delete(_key(session_id))
    except redis.RedisError:
        return
