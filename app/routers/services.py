from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.service import Service
from app.models.user import User
from app.schemas.common import ServiceCreate, ServiceOut, ServiceUpdate

router = APIRouter(prefix="/services", tags=["Services"])


@router.post("", status_code=201)
def create_service(body: ServiceCreate, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    if db.query(Service).filter(Service.slug == body.slug).first():
        raise HTTPException(status_code=409, detail="Slug already exists")
    svc = Service(
        category_id=body.categoryId,
        name=body.name,
        slug=body.slug,
        description=body.description,
        is_active=body.isActive,
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)
    return ServiceOut.model_validate(svc)


@router.get("", status_code=200)
def list_services(
    categoryId: Optional[UUID] = Query(None),
    isActive: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sortBy: str = Query("display_order"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Service)
    if categoryId:
        q = q.filter(Service.category_id == categoryId)
    if isActive is not None:
        q = q.filter(Service.is_active == isActive)
    if search:
        q = q.filter(Service.name.ilike(f"%{search}%"))

    col = getattr(Service, sortBy, Service.display_order)
    q = q.order_by(col.desc() if order == "desc" else col.asc())
    total = q.count()
    items = q.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "items": [ServiceOut.model_validate(s) for s in items]}


@router.patch("/{id}", status_code=200)
def update_service(
    id: UUID,
    body: ServiceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    svc = db.query(Service).filter(Service.id == id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    if body.name is not None:
        svc.name = body.name
    if body.description is not None:
        svc.description = body.description
    if body.isActive is not None:
        svc.is_active = body.isActive
    db.commit()
    db.refresh(svc)
    return ServiceOut.model_validate(svc)
