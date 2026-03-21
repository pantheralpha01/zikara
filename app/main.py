from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import SessionLocal, engine
from app.db.init_models import Base
from app.routers import (
    auth,
    users,
    partners,
    agents,
    managers,
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
from app.routers import admin
from app.services.snapshot import take_daily_snapshot


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        lambda: take_daily_snapshot(SessionLocal()),
        "cron",
        hour=0,
        minute=5,
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


# Create tables on startup (use Alembic migrations in production instead)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Zikara Tours API", version="1.0.0", lifespan=lifespan)

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
app.include_router(managers.router)
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
app.include_router(admin.router)


@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "service": "Zikara Tours API"}
