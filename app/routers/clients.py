from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.models.profile import ClientProfile
from app.models.user import User
from app.schemas.common import UserOut

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.get("", status_code=200)
def list_clients(db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    clients = db.query(User).filter(User.role == "client", User.is_deleted == False).all()
    return [UserOut.model_validate(c) for c in clients]


@router.get("/{id}", status_code=200)
def get_client(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    client = db.query(User).filter(User.id == id, User.role == "client", User.is_deleted == False).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return UserOut.model_validate(client)
