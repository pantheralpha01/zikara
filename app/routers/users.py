from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ManagerCreateRequest, UserOut, UserUpdateRequest

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
