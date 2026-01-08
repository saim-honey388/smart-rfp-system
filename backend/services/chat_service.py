from pathlib import Path
from backend.services import proposal_service, rfp_service
from backend.src.utils.llm_client import complete


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
    
    # Build comprehensive context from ALL stored DB fields
    context_parts = [
        "# Proposal Information (from Database)",
        f"**Contractor**: {proposal.contractor}",
        f"**Status**: {proposal.status}",
    ]
    
    if proposal.price:
        context_parts.append(f"**Total Price**: ${proposal.price:,.2f} {proposal.currency}")
    
    if proposal.start_date:
        context_parts.append(f"**Start Date**: {proposal.start_date}")
    
    if proposal.summary:
        context_parts.append(f"\n**Executive Summary**: {proposal.summary}")
    
    # Enhanced extraction fields (bullet point arrays from DB)
    def add_list_field(title, items):
        if items and len(items) > 0:
            context_parts.append(f"\n**{title}**:")
            for item in items:
                context_parts.append(f"  • {item}")
    
    add_list_field("Experience", getattr(proposal, 'experience', None))
    add_list_field("Scope Understanding", getattr(proposal, 'scope_understanding', None))
    add_list_field("Materials & Equipment", getattr(proposal, 'materials', None))
    add_list_field("Timeline", getattr(proposal, 'timeline', None))
    add_list_field("Warranty Terms", getattr(proposal, 'warranty', None))
    add_list_field("Safety Practices", getattr(proposal, 'safety', None))
    add_list_field("Cost Breakdown", getattr(proposal, 'cost_breakdown', None))
    add_list_field("Termination Terms", getattr(proposal, 'termination_term', None))
    add_list_field("References", getattr(proposal, 'references', None))
    
    # Legacy fields (for backward compatibility)
    if proposal.methodology:
        context_parts.append(f"\n**Methodology**: {proposal.methodology}")
    
    if proposal.timeline_details:
        context_parts.append(f"\n**Timeline Details**: {proposal.timeline_details}")
    
    if proposal.warranties:
        context_parts.append(f"\n**Warranties**: {proposal.warranties}")
    
    # Vendor Bid Form Data (line items from proposal form) - FULLY DYNAMIC
    if proposal.proposal_form_data:
        context_parts.append("\n# Vendor Bid Form (All Line Items)")
        for i, row in enumerate(proposal.proposal_form_data[:50]):  # Limit to 50 rows
            row_parts = []
            
            # Iterate ALL keys dynamically - no hardcoded field names
            for key, value in row.items():
                if key == 'values':
                    # Handle nested 'values' structure (new format with ColumnValuePair)
                    if isinstance(value, list) and value:
                        for v in value:
                            col_name = v.get('column', '') if isinstance(v, dict) else ''
                            col_val = v.get('value', '') if isinstance(v, dict) else str(v)
                            if col_name and col_val:
                                row_parts.append(f"{col_name}: {col_val}")
                    elif isinstance(value, dict) and value:
                        for k, v in value.items():
                            row_parts.append(f"{k}: {v}")
                elif value and str(value).strip() and str(value).strip() != 'None':
                    # Add any non-empty field
                    row_parts.append(f"{key}: {value}")
            
            if row_parts:
                context_parts.append(f"  • Row {i+1}: {', '.join(row_parts)}")
    
    # Add RFP context
    if rfp:
        context_parts.append(f"\n# RFP Information")
        context_parts.append(f"**Title**: {rfp.title}")
        if rfp.budget is not None:
             context_parts.append(f"**Budget**: ${rfp.budget:,.0f} {rfp.currency}")
        else:
             context_parts.append(f"**Budget**: TBD")
        
        if rfp.requirements:
            context_parts.append("\n**RFP Requirements**:")
            for req in rfp.requirements:
                context_parts.append(f"  • {req.text}")
    
    # Skip extracted_text - we now have structured data!
    # Only use as fallback if no structured data
    has_structured_data = any([
        proposal.proposal_form_data,
        getattr(proposal, 'experience', None),
        getattr(proposal, 'cost_breakdown', None),
        proposal.summary
    ])
    
    if not has_structured_data and proposal.extracted_text:
        context_parts.append(f"\n# Raw Proposal Text (fallback)")
        context_parts.append(proposal.extracted_text[:2000])
    
    context_str = "\n".join(context_parts)
    system_prompt = _load_chat_prompt()

    # Limit history to last 5 turns
    recent_history = history[-10:] if history else []
    
    # Enhanced system prompt
    concise_system = system_prompt + """
IMPORTANT INSTRUCTIONS:
- BE EXTREMELY CONCISE. Answer the user's latest question directly.
- Use the structured data above (from Database) as your PRIMARY source.
- Do NOT search for information - it's already provided in the context.
- If asked about prices, quantities, or line items, refer to the Vendor Bid Form.
- If you can't find the information in the database or summary, don't create false information. Politely tell the user that the information may not be provided in the document and they can contact the vendor for clarification.
- If asked about experience, warranty, or methodology, use those specific sections.

COMPARISON CAPABILITIES:
- You have BOTH the RFP Information (requirements, budget) AND the Proposal Information (vendor bid form, pricing, experience).
- When asked to compare RFP requirements with the proposal, cross-reference both sections.
- For example: "Does this proposal meet the RFP budget?" → Compare RFP Budget with Proposal Total Price.
- For example: "Does vendor address requirement X?" → Check if the proposal data covers that RFP requirement.
- Highlight any gaps or matches between what the RFP asks for and what the proposal offers."""
    
    # Clear separation of context and query
    final_prompt = f"Complete Proposal Data (from Database):\n---\n{context_str}\n---\n\n"
    if recent_history:
        final_prompt += "Recent Conversation History:\n"
        for msg in recent_history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            final_prompt += f"{role}: {msg.get('content')}\n"
        final_prompt += "\n"
    
    final_prompt += f"LATEST USER QUESTION (Answer using the data above): {message}"
    
    try:
        return complete(concise_system, final_prompt, temperature=0.5)
    except Exception as e:
        print(f"DEBUG: Chat Error: {e}")
        return f"I apologize, but I encountered an error processing your request. Please try again or rephrase your question."

