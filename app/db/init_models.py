from app.db.base import Base  # noqa: F401

# import all models so SQLAlchemy metadata is populated for Alembic
from app.models.user import User  # noqa: F401
from app.models.profile import AgentProfile, PartnerProfile, ClientProfile  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.service import Service  # noqa: F401
from app.models.listing import Listing  # noqa: F401
from app.models.quote import Quote  # noqa: F401
from app.models.contract import ClientContract, PartnerContract, AgentContract  # noqa: F401
from app.models.booking import Booking, BookingPartner  # noqa: F401
from app.models.payment import Payment, Wallet, WalletTransaction, WithdrawalRequest  # noqa: F401
from app.models.refund_dispute import Refund, Dispute  # noqa: F401
from app.models.review import Review  # noqa: F401
from app.models.otp import OtpCode  # noqa: F401
from app.models.worklog import AgentWorkLog  # noqa: F401
from app.models.stats import (  # noqa: F401
    PlatformStats,
    AgentStats,
    AgentDailyStats,
    PartnerStats,
    PartnerDailyStats,
)
from app.models.enquiry import Enquiry  # noqa: F401
