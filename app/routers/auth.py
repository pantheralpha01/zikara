from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.db.session import get_db
from app.models.profile import AgentProfile, ClientProfile, PartnerProfile
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    AgentApplyRequest,
    ClientSignupRequest,
    LoginRequest,
    PartnerSignupRequest,
    RefreshRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/client/signup", status_code=status.HTTP_201_CREATED)
def client_signup(body: ClientSignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        full_name=body.fullName,
        email=body.email,
        password_hash=hash_password(body.password),
        phone=body.phone,
        gender=body.gender,
        profile_pic_url=body.profilePicUrl,
        role="client",
        status="active",
    )
    db.add(user)
    db.flush()
    db.add(ClientProfile(user_id=user.id))
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "role": user.role, "status": user.status}


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email, User.is_deleted == False).first()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.status == "suspended":
        raise HTTPException(status_code=403, detail="Account suspended")

    access = create_access_token(str(user.id), user.role)
    refresh = create_refresh_token(str(user.id), user.role)
    user.refresh_token = refresh
    db.commit()
    return TokenResponse(accessToken=access, refreshToken=refresh)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.refreshToken)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == payload["sub"], User.is_deleted == False).first()
    if not user or user.refresh_token != body.refreshToken:
        raise HTTPException(status_code=401, detail="Refresh token mismatch or user not found")

    access = create_access_token(str(user.id), user.role)
    return AccessTokenResponse(accessToken=access)


@router.post("/logout", status_code=200)
def logout(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.refresh_token = None
    db.commit()
    return {"message": "Logged out"}


@router.post("/agent/apply", status_code=status.HTTP_201_CREATED)
def agent_apply(body: AgentApplyRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        full_name=body.fullName,
        email=body.email,
        password_hash=hash_password(body.password),
        phone=body.phone,
        gender=body.gender,
        profile_pic_url=body.profilePicUrl,
        role="agent",
        status="pending",
    )
    db.add(user)
    db.flush()
    db.add(AgentProfile(
        user_id=user.id,
        id_number=body.idNumber,
        id_type=body.idType,
        age=body.age,
        town=body.town,
        city=body.city,
        country=body.country,
        education_level=body.educationLevel,
        english_level=body.englishLevel,
        computer_experience=body.computerExperience,
        have_a_computer=body.haveAComputer if body.haveAComputer is not None else False,
        access_to_internet=body.accessToInternet if body.accessToInternet is not None else False,
        internet_speed=body.internetSpeed,
        description_of_self=body.descriptionOfSelf,
    ))
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "role": user.role, "status": user.status}


@router.post("/partner/signup", status_code=status.HTTP_201_CREATED)
def partner_signup(body: PartnerSignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        full_name=f"{body.contactFirstName} {body.contactLastName}",
        email=body.email,
        password_hash=hash_password(body.password),
        phone=body.phone,
        gender=body.gender,
        profile_pic_url=body.profilePicUrl,
        role="partner",
        status="pending",
    )
    db.add(user)
    db.flush()
    profile = PartnerProfile(
        user_id=user.id,
        contact_first_name=body.contactFirstName,
        contact_last_name=body.contactLastName,
        id_number=body.idNumber,
        id_type=body.idType,
        business_name=body.businessName,
        website=body.website,
        description=body.description,
        services_provided=body.servicesProvided,
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "role": user.role, "status": user.status}
