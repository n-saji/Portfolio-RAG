import os
import redis
from dotenv import load_dotenv
import uuid

load_dotenv()


USE_REDIS = os.getenv("USE_REDIS_MEMORY", "false").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.from_url(REDIS_URL) if USE_REDIS else None

def get_chat_history(session_id: str) -> str:
    """Fetches the formatted chat history for the prompt."""
    if not USE_REDIS or not redis_client:
        return "No memory configured."
    
    key = f"session:{session_id}"
    
    # Fetch all messages in the current bounded list
    messages = redis_client.lrange(key, 0, -1)
    
    if not messages:
        return "No previous history."
        
    return "\n".join([msg.decode("utf-8") for msg in messages])

def save_exchange(session_id: str, human_query: str, ai_response: str):
    """Saves the Q&A pair and strictly enforces the 5-conversation limit."""
    if not USE_REDIS or not redis_client:
        return
    if not session_id:
        print("Warning: No session ID provided, skipping memory save.")
        return
        
    key = f"session:{session_id}"
    
    redis_client.rpush(key, f"User: {human_query}")
    redis_client.rpush(key, f"AI: {ai_response}")
    
    # Keep only the last 10 elements (5 exchanges)
    redis_client.ltrim(key, -10, -1)
    
    # TTL for 24 hours
    redis_client.expire(key, 86400)

def clear_session_history(session_id: str):
    """Clears the entire chat history for a given session."""
    if not USE_REDIS or not redis_client:
        return
    key = f"session:{session_id}"
    redis_client.delete(key)

def create_session_id() -> str:
    """Creates a unique session ID. In production, consider using UUIDs."""
    return str(uuid.uuid4())