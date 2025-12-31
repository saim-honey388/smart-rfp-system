from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    proposal_id: str
    message: str = Field(..., example="What are the payment terms?")
    conversation_history: list[dict] = Field(default_factory=list)



class ChatResponse(BaseModel):
    reply: str


# --- RFP Creation Chat Schemas ---

class RFPState(BaseModel):
    title: str = ""
    scope: str = ""
    requirements: list[str] = []
    budget: str = ""
    timeline_end: str = ""  # Keeping it simple mostly just "TBD" or a date string

class RFPChatRequest(BaseModel):
    message: str
    current_state: RFPState
    conversation_history: list[dict] = []  # List of {role: 'user'|'ai', text: str}

class RFPChatResponse(BaseModel):
    reply: str
    updated_state: RFPState

