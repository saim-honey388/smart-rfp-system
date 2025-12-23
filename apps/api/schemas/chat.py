from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    proposal_id: str
    message: str = Field(..., example="What are the payment terms?")


class ChatResponse(BaseModel):
    reply: str

