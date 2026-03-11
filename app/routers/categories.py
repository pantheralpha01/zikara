from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.category import Category
from app.models.user import User
from app.schemas.common import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("", status_code=201)
def create_category(body: CategoryCreate, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    if db.query(Category).filter(Category.slug == body.slug).first():
        raise HTTPException(status_code=409, detail="Slug already exists")
    cat = Category(
        name=body.name,
        slug=body.slug,
        is_active=body.isActive,
        attributes_schema=[a.model_dump(mode='json') for a in body.attributesSchema],
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return CategoryOut.model_validate(cat)


@router.get("", status_code=200)
def list_categories(
    isActive: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sortBy: str = Query("display_order"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Category)
    if isActive is not None:
        q = q.filter(Category.is_active == isActive)
    if search:
        q = q.filter(Category.name.ilike(f"%{search}%"))

    col = getattr(Category, sortBy, Category.display_order)
    q = q.order_by(col.desc() if order == "desc" else col.asc())
    total = q.count()
    items = q.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "items": [CategoryOut.model_validate(c) for c in items]}


@router.patch("/{id}", status_code=200)
def update_category(
    id: UUID,
    body: CategoryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    cat = db.query(Category).filter(Category.id == id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    if body.name is not None:
        cat.name = body.name
    if body.slug is not None:
        cat.slug = body.slug
    if body.isActive is not None:
        cat.is_active = body.isActive
    if body.attributesSchema is not None:
        cat.attributes_schema = body.attributesSchema
    db.commit()
    db.refresh(cat)
    return CategoryOut.model_validate(cat)


@router.delete("/{id}", status_code=200)
def delete_category(id: UUID, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    cat = db.query(Category).filter(Category.id == id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(cat)
    db.commit()
    return {"message": "Category deleted"}
