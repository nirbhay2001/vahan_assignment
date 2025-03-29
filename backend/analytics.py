from copy import deepcopy
import logging
from session_manager import get_chat_history 

logger = logging.getLogger(__name__)
analytics_data = {
    "total_questions": 0,
    "question_types": {
        "travel": 0,
        "support": 0,
        "others": 0
    },
    "repeat_questions": 0
}
def update_analytics(question: str, category: str, session_id: str):
    global analytics_data
    analytics_copy = deepcopy(analytics_data) 
    print(f"session id in update_analytics {session_id}") 
    analytics_copy["total_questions"] += 1
    if category in analytics_copy["question_types"]:
        analytics_copy["question_types"][category] += 1
    else:
        analytics_copy["question_types"]["others"] += 1

    history = get_chat_history(session_id)
    question_str = getattr(question, "query", str(question))
    if any(msg["user"].lower() == question_str.lower() for msg in history[-5:]):
        analytics_copy["repeat_questions"] += 1
    analytics_data.clear()  
    analytics_data.update(analytics_copy)  
    logger.info(f"Updated analytics: {analytics_data}")

