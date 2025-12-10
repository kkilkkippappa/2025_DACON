from fastapi import APIRouter

from app.logging_config import get_logger

router = APIRouter(prefix='/chat', tags=['chat'])
logger = get_logger(__name__)

@router.get("/")
def home():
    return {"message" : "hello, chat page!"}

@router.get("/send")
async def LLM_call():
    """chatGPT에게 채팅 메세지 전달"""
    try:
        #OpenAI 호출
        pass

    except Exception as exc:  # pragma: no cover - placeholder logic
        logger.exception("Chat LLM call failed")
        return {"status": "error", "error_message": str(exc)}
