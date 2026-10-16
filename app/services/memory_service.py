"""Optional, bounded session memory. All failures degrade to stateless chat."""

import json
import logging
import os
import uuid
from functools import lru_cache

logger = logging.getLogger(__name__)


def create_session_id() -> str:
    return str(uuid.uuid4())


@lru_cache(maxsize=1)
def _client():
    if os.getenv("USE_REDIS_MEMORY", "false").lower() != "true":
        return None
    try:
        import redis

        return redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            socket_connect_timeout=0.35,
            socket_timeout=0.35,
            decode_responses=True,
        )
    except Exception:
        logger.exception("redis initialization failed")
        return None


def get_turns(session_id: str | None) -> list[dict[str, str]]:
    client = _client()
    if client is None or not session_id:
        return []
    try:
        turns = [json.loads(item) for item in client.lrange(f"session:{session_id}", -8, -1)]
        return [t for t in turns if t.get("role") in {"user", "assistant"} and isinstance(t.get("content"), str)]
    except Exception:
        logger.warning("redis read failed", exc_info=True)
        return []


def save_exchange(session_id: str | None, human_query: str, ai_response: str) -> None:
    client = _client()
    if client is None or not session_id:
        return
    try:
        key = f"session:{session_id}"
        pipe = client.pipeline()
        pipe.rpush(key, json.dumps({"role": "user", "content": human_query}))
        pipe.rpush(key, json.dumps({"role": "assistant", "content": ai_response}))
        pipe.ltrim(key, -8, -1)
        pipe.expire(key, 86400)
        pipe.execute()
    except Exception:
        logger.warning("redis write failed", exc_info=True)
