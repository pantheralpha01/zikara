from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.profile import AgentProfile, PartnerProfile
from app.models.user import User
from app.schemas.common import (
    AgentSelfOut,
    AgentSelfUpdate,
    ManagerCreateRequest,
    PartnerSelfOut,
    PartnerSelfUpdate,
    UserOut,
    UserUpdateRequest,
    AgentProfileOut,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(body: UserUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.phone is not None:
        current_user.phone = body.phone
    if body.gender is not None:
        current_user.gender = body.gender
    if body.profile_pic_url is not None:
        current_user.profile_pic_url = body.profile_pic_url
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me", status_code=200)
def delete_me(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.is_deleted = True
    current_user.refresh_token = None
    db.commit()
    return {"message": "Account deleted"}


# ── Manager self endpoints ────────────────────────────────────────────────────

@router.get("/manager/me", response_model=AgentSelfOut, summary="Get own manager profile")
def get_manager_me(db: Session = Depends(get_db), current_user: User = Depends(require_role("manager"))):
    profile = db.query(AgentProfile).filter(AgentProfile.user_id == current_user.id).first()
    return AgentSelfOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        gender=current_user.gender,
        profile_pic_url=current_user.profile_pic_url,
        role=current_user.role,
        status=current_user.status,
        created_at=current_user.created_at,
        profile=AgentProfileOut.model_validate(profile) if profile else None,
    )


# ── Agent self endpoints ──────────────────────────────────────────────────────

@router.get("/agent/me", response_model=AgentSelfOut, summary="Get own agent profile")
def get_agent_me(db: Session = Depends(get_db), current_user: User = Depends(require_role("agent"))):
    profile = db.query(AgentProfile).filter(AgentProfile.user_id == current_user.id).first()
    from app.schemas.common import AgentProfileOut
    return AgentSelfOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        gender=current_user.gender,
        profile_pic_url=current_user.profile_pic_url,
        role=current_user.role,
        status=current_user.status,
        created_at=current_user.created_at,
        profile=AgentProfileOut.model_validate(profile) if profile else None,
    )


@router.patch(
    "/agent/me",
    response_model=AgentSelfOut,
    summary="Update own agent profile (restricted fields)",
    description="Agents may only update: phone, availability, hoursPerWeekAvailable, profilePicture.",
)
def update_agent_me(
    body: AgentSelfUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    if body.phone is not None:
        current_user.phone = body.phone
    if body.profile_pic_url is not None:
        current_user.profile_pic_url = body.profile_pic_url

    profile = db.query(AgentProfile).filter(AgentProfile.user_id == current_user.id).first()
    if profile:
        if body.availability is not None:
            profile.availability = body.availability
        if body.hours_per_week_available is not None:
            profile.hours_per_week_available = body.hours_per_week_available

    db.commit()
    db.refresh(current_user)
    from app.schemas.common import AgentProfileOut
    return AgentSelfOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        gender=current_user.gender,
        profile_pic_url=current_user.profile_pic_url,
        role=current_user.role,
        status=current_user.status,
        created_at=current_user.created_at,
        profile=AgentProfileOut.model_validate(profile) if profile else None,
    )


# ── Partner self endpoints ────────────────────────────────────────────────────

@router.get("/partners/me", response_model=PartnerSelfOut, summary="Get own partner profile")
def get_partner_me(db: Session = Depends(get_db), current_user: User = Depends(require_role("partner"))):
    profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == current_user.id).first()
    from app.schemas.common import PartnerProfileOut
    return PartnerSelfOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        gender=current_user.gender,
        profile_pic_url=current_user.profile_pic_url,
        role=current_user.role,
        status=current_user.status,
        created_at=current_user.created_at,
        profile=PartnerProfileOut.model_validate(profile) if profile else None,
    )


@router.patch(
    "/partners/me",
    response_model=PartnerSelfOut,
    summary="Update own partner profile (restricted fields)",
    description="Partners may only update: phone, availability, hoursPerWeekAvailable, profilePicture.",
)
def update_partner_me(
    body: PartnerSelfUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("partner")),
):
    if body.phone is not None:
        current_user.phone = body.phone
    if body.profile_pic_url is not None:
        current_user.profile_pic_url = body.profile_pic_url

    profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == current_user.id).first()
    if profile:
        if body.availability is not None:
            profile.availability = body.availability
        if body.hours_per_week_available is not None:
            profile.hours_per_week_available = body.hours_per_week_available

    db.commit()
    db.refresh(current_user)
    from app.schemas.common import PartnerProfileOut
    return PartnerSelfOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        gender=current_user.gender,
        profile_pic_url=current_user.profile_pic_url,
        role=current_user.role,
        status=current_user.status,
        created_at=current_user.created_at,
        profile=PartnerProfileOut.model_validate(profile) if profile else None,
    )


# ── Manager management (admin-only create / deactivate) ──────────────────────

@router.post("/managers", response_model=UserOut, status_code=201)
def create_manager(body: ManagerCreateRequest, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    if db.query(User).filter(User.email == body.email, User.is_deleted == False).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    manager = User(
        full_name=body.fullName,
        email=body.email,
        password_hash=hash_password(body.password),
        phone=body.phone,
        gender=body.gender,
        profile_pic_url=body.profilePicUrl,
        role="manager",
        status="active",
    )
    db.add(manager)
    db.flush()
    db.add(AgentProfile(
        user_id=manager.id,
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
        availability=body.availability,
        hours_per_week_available=body.hoursPerWeekAvailable,
    ))
    db.commit()
    db.refresh(manager)
    return manager


@router.post("/managers/{id}/deactivate", status_code=200)
def deactivate_manager(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    manager = db.query(User).filter(User.id == id, User.role == "manager", User.is_deleted == False).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    manager.status = "suspended"
    manager.refresh_token = None
    db.commit()
    return {"message": "Manager deactivated"}


# ── Self-deactivation endpoints ───────────────────────────────────────────────

@router.post("/manager/me/deactivate", status_code=200, summary="Manager self-deactivation")
def deactivate_manager_me(db: Session = Depends(get_db), current_user: User = Depends(require_role("manager"))):
    current_user.status = "suspended"
    current_user.refresh_token = None
    db.commit()
    return {"message": "Account deactivated"}


@router.post("/agent/me/deactivate", status_code=200, summary="Agent self-deactivation")
def deactivate_agent_me(db: Session = Depends(get_db), current_user: User = Depends(require_role("agent"))):
    current_user.status = "suspended"
    current_user.refresh_token = None
    db.commit()
    return {"message": "Account deactivated"}


@router.post("/partners/me/deactivate", status_code=200, summary="Partner self-deactivation")
def deactivate_partner_me(db: Session = Depends(get_db), current_user: User = Depends(require_role("partner"))):
    current_user.status = "suspended"
    current_user.refresh_token = None
    db.commit()
    return {"message": "Account deactivated"}
