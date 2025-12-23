from fastapi import APIRouter, HTTPException

from apps.api.schemas.chat import ChatRequest, ChatResponse
from apps.api.services import chat_service, proposal_service

router = APIRouter(tags=["chat"])


@router.post("/proposals/{proposal_id}/chat", response_model=ChatResponse)
def chat_with_proposal(proposal_id: str, body: ChatRequest):
    if not proposal_service.get_proposal(proposal_id):
        raise HTTPException(status_code=404, detail="Proposal not found")
    reply = chat_service.ask_about_proposal(proposal_id, body.message)
    return ChatResponse(reply=reply)

