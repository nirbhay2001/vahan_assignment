import redis
import json
import uuid
import logging  
from fastapi import Request, Response
from typing import List, Dict

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
try:
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3
    )
    redis_client.ping()  
except redis.ConnectionError:
    raise RuntimeError("Redis server connection failed")

def get_session_id(request: Request, response: Response) -> str:
    session_id = request.cookies.get("session_id")
    
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.debug(f"Creating NEW session: {session_id}")
        
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=False,  
            samesite='lax',  
            max_age=3600*24*7,  
            path="/",
        )
    else:
        logger.debug(f"Using EXISTING session: {session_id}")  
    return session_id

def get_chat_history(session_id: str) -> List[Dict[str, str]]:
    try:
        history = redis_client.get(session_id)
        return json.loads(history) if history else []
    except json.JSONDecodeError:
        return []
    except redis.RedisError as e:
        logger.error(f"Redis error: {e}")
        return []

def update_chat_history(session_id: str, user_message: str, bot_response: str):
    try:
        history = get_chat_history(session_id)
        history.append({"user": user_message, "bot": bot_response})
        if len(history) > 10:  
            history = history[-10:]
            
        redis_client.setex(
            session_id,
            time=3600*24*7,  
            value=json.dumps(history)
        )
    except Exception as e:
        logger.error(f"History update failed: {e}")