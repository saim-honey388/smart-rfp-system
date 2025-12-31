from pathlib import Path
from apps.api.services import proposal_service, rfp_service
from services.review.llm_client import complete


def _load_chat_prompt() -> str:
    """Load the chat system prompt template."""
    prompt_path = Path(__file__).parent.parent.parent / "services" / "ingest" / "prompts" / "chat_prompt.txt"
    if prompt_path.exists():
        return prompt_path.read_text()
    # Fallback if file doesn't exist
    return "You are a helpful assistant analyzing RFP proposals. Provide clear, structured responses using markdown formatting."


def ask_about_proposal(proposal_id: str, message: str, history: list[dict] = []) -> str:
    proposal = proposal_service.get_proposal(proposal_id)
    if not proposal:
        return "Proposal not found."
    
    rfp = rfp_service.get_rfp(proposal.rfp_id)
    
    # Build comprehensive context
    context_parts = [
        "# Proposal Information",
        f"**Contractor**: {proposal.contractor}",
    ]
    
    if proposal.price:
        context_parts.append(f"**Price**: {proposal.price:,.0f} {proposal.currency}")
    
    if proposal.start_date:
        context_parts.append(f"**Start Date**: {proposal.start_date}")
    
    if proposal.summary:
        context_parts.append(f"\n**Summary**: {proposal.summary}")
    
    if proposal.experience:
        context_parts.append(f"\n**Experience**: {proposal.experience}")
    
    if proposal.methodology:
        context_parts.append(f"\n**Methodology**: {proposal.methodology}")
    
    if proposal.timeline_details:
        context_parts.append(f"\n**Timeline**: {proposal.timeline_details}")
    
    if proposal.warranties:
        context_parts.append(f"\n**Warranties**: {proposal.warranties}")
    
    # Add RFP context
    if rfp:
        context_parts.append(f"\n# RFP Information")
        context_parts.append(f"**Title**: {rfp.title}")
        if rfp.budget is not None:
             context_parts.append(f"**Budget**: {rfp.budget:,.0f} {rfp.currency}")
        else:
             context_parts.append(f"**Budget**: TBD")
        
        if rfp.requirements:
            context_parts.append("\n**Requirements**:")
            for req in rfp.requirements:
                context_parts.append(f"- {req.text}")
    
    # Add extracted text (truncated)
    if proposal.extracted_text:
        context_parts.append(f"\n# Full Proposal Text (excerpt)")
        context_parts.append(proposal.extracted_text[:3000])
    
    context_str = "\n".join(context_parts)
    system_prompt = _load_chat_prompt()

    # Limit history to last 5 turns to prevent "combining" confusion and keep responses focused
    recent_history = history[-10:] if history else []
    
    # Reinforce conciseness in the system call
    concise_system = system_prompt + "\nIMPORTANT: BE EXTREMELY CONCISE. Answer the user's latest question directly. Do not summarize the whole conversation unless asked."
    
    # Clear separation of context and query
    final_prompt = f"Context from Proposal:\n---\n{context_str}\n---\n\n"
    if recent_history:
        final_prompt += "Recent Conversation History:\n"
        for msg in recent_history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            final_prompt += f"{role}: {msg.get('content')}\n"
        final_prompt += "\n"
    
    final_prompt += f"LATEST USER QUESTION (Answer this briefly): {message}"
    
    try:
        return complete(concise_system, final_prompt, temperature=0.7)
    except Exception as e:
        print(f"DEBUG: Chat Error: {e}")
        return f"I apologize, but I encountered an error processing your request. Please try again or rephrase your question."
