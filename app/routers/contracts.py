from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.contract import AgentContract, ClientContract, PartnerContract
from app.models.user import User
from app.schemas.transactions import (
    AgentContractCreate,
    AgentContractOut,
    AgentContractUpdate,
    ClientContractCreate,
    ClientContractOut,
    ClientContractUpdate,
    PartnerContractCreate,
    PartnerContractOut,
    PartnerContractUpdate,
)

router = APIRouter(prefix="/contracts", tags=["Contracts"])


# ── Client contracts ─────────────────────────────────────────────────────────

@router.post("/client", status_code=201)
def create_client_contract(body: ClientContractCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    contract = ClientContract(
        customer_name=body.customerName,
        customer_phone_number=body.customerPhoneNumber,
        customer_email=body.customerEmail,
        file_url=body.fileurl,
        service_title=body.serviceTitle,
        agent_id=body.agentId,
        currency=body.currency,
        partners=[p.model_dump() for p in body.partners],
        total_amount=body.totalAmount,
        payment_type=body.paymentType,
        cost_at_booking=body.costAtBooking,
        cost_post_event=body.costPostEvent,
        pay_post_event_due_date=body.payPostEventDueDate,
        pickup_location=body.pickupLocation,
        destination=body.destination,
        number_of_guests=body.numberOfGuests,
        service_start_at=body.serviceStartAt,
        service_end_at=body.serviceEndAt,
        service_timezone=body.serviceTimezone,
        signed_at=body.signedAt,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return ClientContractOut.model_validate(contract)


@router.get("/clients", status_code=200)
def list_client_contracts(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return [ClientContractOut.model_validate(c) for c in db.query(ClientContract).all()]


@router.get("/clients/{id}", status_code=200)
def get_client_contract(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    c = db.query(ClientContract).filter(ClientContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    return ClientContractOut.model_validate(c)


@router.patch("/clients/{id}", status_code=200)
def update_client_contract(id: UUID, body: ClientContractUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    c = db.query(ClientContract).filter(ClientContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return ClientContractOut.model_validate(c)


@router.delete("/clients/{id}", status_code=200)
def delete_client_contract(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    c = db.query(ClientContract).filter(ClientContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    db.delete(c)
    db.commit()
    return {"message": "Contract deleted"}


# ── Partner contracts ─────────────────────────────────────────────────────────

@router.post("/partner", status_code=201)
def create_partner_contract(body: PartnerContractCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    contract = PartnerContract(
        partner_id=body.partnerID,
        reference_id=body.referenceID,
        file_url=body.fileurl,
        signed_at=body.signedAt,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return PartnerContractOut.model_validate(contract)


@router.get("/partners", status_code=200)
def list_partner_contracts(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return [PartnerContractOut.model_validate(c) for c in db.query(PartnerContract).all()]


@router.get("/partners/{id}", status_code=200)
def get_partner_contract(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    c = db.query(PartnerContract).filter(PartnerContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    return PartnerContractOut.model_validate(c)


@router.patch("/partners/{id}", status_code=200)
def update_partner_contract(id: UUID, body: PartnerContractUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    c = db.query(PartnerContract).filter(PartnerContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return PartnerContractOut.model_validate(c)


@router.delete("/partners/{id}", status_code=200)
def delete_partner_contract(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    c = db.query(PartnerContract).filter(PartnerContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    db.delete(c)
    db.commit()
    return {"message": "Contract deleted"}


# ── Agent contracts ───────────────────────────────────────────────────────────

@router.post("/agent", status_code=201)
def create_agent_contract(body: AgentContractCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    contract = AgentContract(
        agent_id=body.agentID,
        reference_id=body.referenceID,
        file_url=body.fileurl,
        signed_at=body.signedAt,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return AgentContractOut.model_validate(contract)


@router.get("/agents", status_code=200)
def list_agent_contracts(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return [AgentContractOut.model_validate(c) for c in db.query(AgentContract).all()]


@router.get("/agents/{id}", status_code=200)
def get_agent_contract(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    c = db.query(AgentContract).filter(AgentContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    return AgentContractOut.model_validate(c)


@router.patch("/agents/{id}", status_code=200)
def update_agent_contract(id: UUID, body: AgentContractUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    c = db.query(AgentContract).filter(AgentContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return AgentContractOut.model_validate(c)


@router.delete("/agents/{id}", status_code=200)
def delete_agent_contract(id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    c = db.query(AgentContract).filter(AgentContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    db.delete(c)
    db.commit()
    return {"message": "Contract deleted"}
