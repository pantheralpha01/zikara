import random
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.otp import OtpCode
from app.schemas.otp import OtpSendRequest, OtpSendResponse, OtpVerifyRequest, OtpVerifyResponse
from app.services.sms import send_otp_sms

router = APIRouter(prefix="/otp", tags=["OTP"])

OTP_EXPIRY_MINUTES = 30


def _generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


@router.post("/send", response_model=OtpSendResponse, status_code=200)
def send_otp(body: OtpSendRequest, db: Session = Depends(get_db)):
    code = _generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    otp = OtpCode(phone=body.phone, code=code, expires_at=expires_at)
    db.add(otp)
    db.commit()

    success = send_otp_sms(body.phone, code)
    if not success:
        raise HTTPException(status_code=502, detail="Failed to send OTP. Please try again.")

    return OtpSendResponse(message="OTP sent successfully.")


@router.post("/verify", response_model=OtpVerifyResponse, status_code=200)
def verify_otp(body: OtpVerifyRequest, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)

    otp = (
        db.query(OtpCode)
        .filter(
            OtpCode.phone == body.phone,
            OtpCode.used == False,
            OtpCode.expires_at > now,
        )
        .order_by(OtpCode.created_at.desc())
        .first()
    )

    if not otp:
        # Check if there's an expired one to give a better error
        expired = (
            db.query(OtpCode)
            .filter(OtpCode.phone == body.phone, OtpCode.used == False)
            .order_by(OtpCode.created_at.desc())
            .first()
        )
        if expired:
            raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
        raise HTTPException(status_code=404, detail="No active OTP found for this number.")

    if otp.code != body.code:
        raise HTTPException(status_code=400, detail="Invalid OTP.")

    otp.used = True
    db.commit()

    return OtpVerifyResponse(verified=True, message="Phone number verified successfully.")
