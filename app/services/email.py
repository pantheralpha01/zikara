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
