from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.contract import AgentContract, ClientContract, PartnerContract
from app.models.profile import PartnerProfile
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


def _get_partner_profile_for_user(user_id: UUID, db: Session) -> PartnerProfile:
    partner = db.query(PartnerProfile).filter(PartnerProfile.user_id == user_id).first()
    if not partner:
        raise HTTPException(status_code=403, detail="Partner profile not found")
    return partner


# ── Client contracts ─────────────────────────────────────────────────────────

@router.post("/client", status_code=201)
def create_client_contract(body: ClientContractCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {"admin", "agent", "client"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    agent_id = body.agentId
    customer_email = body.customerEmail
    if current_user.role == "agent":
        if body.agentId and body.agentId != current_user.id:
            raise HTTPException(status_code=403, detail="Agents can only create contracts for themselves")
        agent_id = current_user.id
    if current_user.role == "client":
        if body.customerEmail and body.customerEmail != current_user.email:
            raise HTTPException(status_code=403, detail="Clients can only use their own email")
        customer_email = current_user.email

    contract = ClientContract(
        customer_name=body.customerName,
        customer_phone_number=body.customerPhoneNumber,
        customer_email=customer_email,
        file_url=body.fileurl,
        service_title=body.serviceTitle,
        agent_id=agent_id,
        currency=body.currency,
        partners=[p.model_dump(mode='json') for p in body.partners],
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
def list_client_contracts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(ClientContract)
    if current_user.role == "admin":
        pass
    elif current_user.role == "agent":
        q = q.filter(ClientContract.agent_id == current_user.id)
    elif current_user.role == "client":
        q = q.filter(ClientContract.customer_email == current_user.email)
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return [ClientContractOut.model_validate(c) for c in q.all()]


@router.get("/clients/{id}", status_code=200)
def get_client_contract(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(ClientContract).filter(ClientContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    if current_user.role == "agent" and c.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to access this contract")
    if current_user.role == "client" and c.customer_email != current_user.email:
        raise HTTPException(status_code=403, detail="You are not allowed to access this contract")
    if current_user.role not in {"admin", "agent", "client"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return ClientContractOut.model_validate(c)


@router.patch("/clients/{id}", status_code=200)
def update_client_contract(id: UUID, body: ClientContractUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {"admin", "agent"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    c = db.query(ClientContract).filter(ClientContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    if current_user.role == "agent" and c.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to update this contract")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return ClientContractOut.model_validate(c)


@router.delete("/clients/{id}", status_code=200)
def delete_client_contract(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    c = db.query(ClientContract).filter(ClientContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    db.delete(c)
    db.commit()
    return {"message": "Contract deleted"}


# ── Partner contracts ─────────────────────────────────────────────────────────

@router.post("/partner", status_code=201)
def create_partner_contract(body: PartnerContractCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {"admin", "partner"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    partner_id = body.partnerID
    if current_user.role == "partner":
        partner = _get_partner_profile_for_user(current_user.id, db)
        if body.partnerID != partner.id:
            raise HTTPException(status_code=403, detail="You can only create contracts for your own partner profile")
        partner_id = partner.id

    contract = PartnerContract(
        partner_id=partner_id,
        reference_id=body.referenceID,
        file_url=body.fileurl,
        signed_at=body.signedAt,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return PartnerContractOut.model_validate(contract)


@router.get("/partners", status_code=200)
def list_partner_contracts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {"admin", "partner"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    q = db.query(PartnerContract)
    if current_user.role == "partner":
        partner = _get_partner_profile_for_user(current_user.id, db)
        q = q.filter(PartnerContract.partner_id == partner.id)
    return [PartnerContractOut.model_validate(c) for c in q.all()]


@router.get("/partners/{id}", status_code=200)
def get_partner_contract(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {"admin", "partner"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    c = db.query(PartnerContract).filter(PartnerContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    if current_user.role == "partner":
        partner = _get_partner_profile_for_user(current_user.id, db)
        if c.partner_id != partner.id:
            raise HTTPException(status_code=403, detail="You are not allowed to access this contract")
    return PartnerContractOut.model_validate(c)


@router.patch("/partners/{id}", status_code=200)
def update_partner_contract(id: UUID, body: PartnerContractUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {"admin", "partner"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    c = db.query(PartnerContract).filter(PartnerContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    if current_user.role == "partner":
        partner = _get_partner_profile_for_user(current_user.id, db)
        if c.partner_id != partner.id:
            raise HTTPException(status_code=403, detail="You are not allowed to update this contract")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return PartnerContractOut.model_validate(c)


@router.delete("/partners/{id}", status_code=200)
def delete_partner_contract(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    c = db.query(PartnerContract).filter(PartnerContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    db.delete(c)
    db.commit()
    return {"message": "Contract deleted"}


# ── Agent contracts ───────────────────────────────────────────────────────────

@router.post("/agent", status_code=201)
def create_agent_contract(body: AgentContractCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {"admin", "agent"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    agent_id = body.agentID
    if current_user.role == "agent":
        if body.agentID != current_user.id:
            raise HTTPException(status_code=403, detail="You can only create contracts for yourself")
        agent_id = current_user.id

    contract = AgentContract(
        agent_id=agent_id,
        reference_id=body.referenceID,
        file_url=body.fileurl,
        signed_at=body.signedAt,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return AgentContractOut.model_validate(contract)


@router.get("/agents", status_code=200)
def list_agent_contracts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {"admin", "agent"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    q = db.query(AgentContract)
    if current_user.role == "agent":
        q = q.filter(AgentContract.agent_id == current_user.id)
    return [AgentContractOut.model_validate(c) for c in q.all()]


@router.get("/agents/{id}", status_code=200)
def get_agent_contract(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {"admin", "agent"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    c = db.query(AgentContract).filter(AgentContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    if current_user.role == "agent" and c.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to access this contract")
    return AgentContractOut.model_validate(c)


@router.patch("/agents/{id}", status_code=200)
def update_agent_contract(id: UUID, body: AgentContractUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {"admin", "agent"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    c = db.query(AgentContract).filter(AgentContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    if current_user.role == "agent" and c.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to update this contract")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return AgentContractOut.model_validate(c)


@router.delete("/agents/{id}", status_code=200)
def delete_agent_contract(id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    c = db.query(AgentContract).filter(AgentContract.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    db.delete(c)
    db.commit()
    return {"message": "Contract deleted"}
