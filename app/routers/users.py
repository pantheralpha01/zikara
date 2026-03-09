from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import UserOut, UserUpdateRequest

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
