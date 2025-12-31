from fastapi import APIRouter, HTTPException

from apps.api.schemas.chat import ChatRequest, ChatResponse, RFPChatRequest, RFPChatResponse
from apps.api.services import chat_service, proposal_service

router = APIRouter(tags=["chat"])


@router.post("/proposals/{proposal_id}/chat", response_model=ChatResponse)
def chat_with_proposal(proposal_id: str, body: ChatRequest):
    if not proposal_service.get_proposal(proposal_id):
        raise HTTPException(status_code=404, detail="Proposal not found")
    reply = chat_service.ask_about_proposal(proposal_id, body.message, body.conversation_history)
    return ChatResponse(reply=reply)


@router.post("/chat/rfp", response_model=RFPChatResponse)
def chat_for_rfp_creation(body: RFPChatRequest):
    """
    Stateful chat for creating an RFP. 
    Receives current state + message -> Returns new state + reply.
    """
    from apps.api.services import rfp_consultant
    
    result = rfp_consultant.consult_on_rfp(
        message=body.message,
        current_state=body.current_state,
        history=body.conversation_history
    )
    
    return RFPChatResponse(
        reply=result["reply"],
        updated_state=result["updated_state"]
    )

