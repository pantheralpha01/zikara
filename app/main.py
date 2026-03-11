from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import engine
from app.db.init_models import Base
from app.routers import (
    auth,
    users,
    partners,
    agents,
    clients,
    categories,
    services,
    listings,
    quotes,
    contracts,
    bookings,
    payments,
    refunds_disputes,
    reviews,
    otp,
)

# Create tables on startup (use Alembic migrations in production instead)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Zikara Tours API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(partners.router)
app.include_router(agents.router)
app.include_router(clients.router)
app.include_router(categories.router)
app.include_router(services.router)
app.include_router(listings.router)
app.include_router(quotes.router)
app.include_router(contracts.router)
app.include_router(bookings.router)
app.include_router(payments.router)
app.include_router(payments.wallet_router)
app.include_router(refunds_disputes.refunds_router)
app.include_router(refunds_disputes.disputes_router)
app.include_router(reviews.router)
app.include_router(otp.router)


@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "service": "Zikara Tours API"}
