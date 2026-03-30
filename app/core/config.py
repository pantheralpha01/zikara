from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENABLE_COOKIE_AUTH: bool = False

    # Brevo SMTP
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_SERVER: str = "smtp-relay.brevo.com"
    MAIL_PORT: int = 587
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    ADMIN_NOTIFICATION_EMAILS: list[str] = []

    FRONTEND_URL: str = "http://localhost:3000"
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 60
    REQUIRE_EMAIL_VERIFICATION: bool = False

    # Chakra HQ integration — inbound (Chakra → Zikara)
    CHAKRA_API_KEY: str = ""

    # Chakra HQ integration — outbound (Zikara → Chakra)
    CHAKRA_BASE_URL: str = ""
    CHAKRA_CLIENT_ID: str = ""
    CHAKRA_CLIENT_SECRET: str = ""
    CHAKRA_ACCESS_TOKEN: str = ""
    CHAKRA_REFRESH_TOKEN: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
