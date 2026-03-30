from typing import Optional

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

from app.core.config import settings

_conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)


async def send_password_reset_email(to_email: str, reset_link: str) -> bool:
    try:
        message = MessageSchema(
            subject="Reset your Zikara password",
            recipients=[to_email],
            body=(
                f"Hello,\n\n"
                f"You requested a password reset. Click the link below to set a new password.\n"
                f"The link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.\n\n"
                f"{reset_link}\n\n"
                f"If you did not request this, you can safely ignore this email."
            ),
            subtype=MessageType.plain,
        )
        fm = FastMail(_conf)
        await fm.send_message(message)
        return True
    except Exception:
        return False


async def send_email_verification_email(to_email: str, verification_link: str) -> bool:
    try:
        message = MessageSchema(
            subject="Verify your Zikara email",
            recipients=[to_email],
            body=(
                f"Hello,\n\n"
                f"Please verify your email address by clicking the link below:\n\n"
                f"{verification_link}\n\n"
                f"This link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES} minutes.\n\n"
                f"If you did not create a Zikara account, you can ignore this message."
            ),
            subtype=MessageType.plain,
        )
        fm = FastMail(_conf)
        await fm.send_message(message)
        return True
    except Exception:
        return False


async def send_simple_email(recipients: list[str], subject: str, body: str) -> bool:
    try:
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=body,
            subtype=MessageType.plain,
        )
        fm = FastMail(_conf)
        await fm.send_message(message)
        return True
    except Exception:
        return False


async def send_withdrawal_request_submitted_email(to_email: str, requester_name: str, amount: float, request_id: str, wallet_owner_type: str) -> bool:
    subject = "Withdrawal request submitted"
    body = (
        f"Hello {requester_name},\n\n"
        f"Your {wallet_owner_type} withdrawal request for {amount:.2f} has been submitted successfully.\n"
        f"Request ID: {request_id}\n\n"
        f"An administrator will review the request and notify you once it is approved or rejected."
    )
    return await send_simple_email([to_email], subject, body)


async def send_withdrawal_request_alert_email(recipients: list[str], requester_name: str, amount: float, request_id: str, wallet_owner_type: str) -> bool:
    subject = "New withdrawal request pending approval"
    body = (
        f"Hello,\n\n"
        f"A new {wallet_owner_type} withdrawal request has been submitted by {requester_name}.\n"
        f"Amount: {amount:.2f}\n"
        f"Request ID: {request_id}\n\n"
        f"Please review and approve or reject this request in the admin dashboard."
    )
    return await send_simple_email(recipients, subject, body)


async def send_withdrawal_request_status_email(to_email: str, requester_name: str, amount: float, request_id: str, approved: bool, review_note: Optional[str] = None) -> bool:
    status_text = "approved" if approved else "rejected"
    subject = f"Withdrawal request {status_text}"
    body = (
        f"Hello {requester_name},\n\n"
        f"Your withdrawal request for {amount:.2f} (ID: {request_id}) has been {status_text}.\n"
    )
    if review_note:
        body += f"\nReview note:\n{review_note}\n"
    body += "\nThank you for using Zikara."
    return await send_simple_email([to_email], subject, body)
