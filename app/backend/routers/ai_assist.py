from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.llm_service import get_ai_assistance

router = APIRouter(prefix="/api/ai-assist", tags=["ai-assist"])


class AIAssistRequest(BaseModel):
    instruction: str
    current_content: str
    field_type: str  # "prompt" or "schema"
    context: str = ""  # Optional context


class AIAssistResponse(BaseModel):
    content: str


@router.post("/generate", response_model=AIAssistResponse)
async def generate_with_ai(request: AIAssistRequest):
    """Use AI to generate or improve prompts and schemas"""
    try:
        result = await get_ai_assistance(
            instruction=request.instruction,
            current_content=request.current_content,
            field_type=request.field_type,
            context=request.context,
        )
        return AIAssistResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
