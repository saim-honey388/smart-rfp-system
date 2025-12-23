"""Email notifications for proposal decisions and RFP expiry."""

import smtplib
from email.message import EmailMessage
from typing import Optional

from apps.api.config.settings import settings
from apps.api.schemas.review import ReviewResult
from services.review.llm_client import complete


def _send_email(to_email: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not to_email:
        # SMTP not configured; fail silently to avoid crashing the app.
        return

    msg = EmailMessage()
    msg["From"] = settings.sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def send_rejection_email(rfp_title: str, contractor_email: str, contractor_name: str, review: ReviewResult) -> None:
    """Use AI to write a clear professional rejection email with missing items."""
    if not contractor_email:
        return
    system = (
        "You are a procurement manager writing clear, professional emails to contractors. "
        "Explain briefly why a proposal was not selected and what was missing, "
        "in a polite and constructive tone. Do not invent facts."
    )
    prompt = (
        f"RFP title: {rfp_title}\n"
        f"Contractor: {contractor_name}\n"
        f"Review scores and risk:\n"
        f"{review.model_dump_json(indent=2)}\n\n"
        "Write an email body (no subject) to the contractor explaining:\n"
        "- That their proposal was not selected.\n"
        "- What key requirements were missing or weak based on the scores.\n"
        "- What they should improve for future opportunities.\n"
        "Keep it under 250 words."
    )
    body = complete(system, prompt, temperature=0.4)
    subject = f"Regarding your proposal for {rfp_title}"
    _send_email(contractor_email, subject, body)


def send_expiry_email(rfp_title: str, contractor_email: str, contractor_name: str) -> None:
    if not contractor_email:
        return
    subject = f"Status update for your proposal - {rfp_title}"
    body = (
        f"Dear {contractor_name},\n\n"
        f"The RFP \"{rfp_title}\" has reached its deadline and the associated proposals "
        "have now expired in our system. This does not reflect negatively on your company; "
        "it simply means that the decision window has closed.\n\n"
        "Thank you for the time and effort you invested in preparing your proposal. "
        "We encourage you to participate in future opportunities.\n\n"
        "Best regards,\n"
        "Procurement Team"
    )
    _send_email(contractor_email, subject, body)


def send_approval_email(rfp_title: str, contractor_email: str, contractor_name: str) -> None:
    if not contractor_email:
        return
    subject = f"Proposal approved for {rfp_title}"
    body = (
        f"Dear {contractor_name},\n\n"
        f"We are pleased to inform you that your proposal for the RFP \"{rfp_title}\" "
        "has been selected to move forward to the negotiation phase.\n\n"
        "Our team will reach out with next steps and any required clarifications. "
        "In the meantime, please ensure your key contacts are available for follow-up discussions.\n\n"
        "Best regards,\n"
        "Procurement Team"
    )
    _send_email(contractor_email, subject, body)


