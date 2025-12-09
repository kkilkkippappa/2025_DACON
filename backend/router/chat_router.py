from fastapi import APIRouter

router = APIRouter(prefix='/chat', tags=['chat'])

@router.get("/")
def home():
    return {"message" : "hello, chat page!"}

@router.get("/send")
async def LLM_call():
    """chatGPT에게 채팅 메세지 전달"""
    try:
        #OpenAI 호출
        pass

    except Exception as e:
        return {"status" : "error", "error message" : {e.msg}}
