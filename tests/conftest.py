"""
Pytest configuration and shared fixtures.

Creates an admin user directly in the database (there is no admin signup
endpoint) and exposes HTTP clients pre-loaded with auth tokens for each role.
All test data is cleaned up via a module-scoped teardown.
"""

import uuid
import pytest
from sqlalchemy import text
from fastapi.testclient import TestClient

# Import all models so SQLAlchemy can resolve all relationships (e.g. Wallet)
import app.db.init_models  # noqa: F401
from app.main import app
from app.core.security import decode_token
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User
from app.models.profile import AgentProfile, ClientProfile, PartnerProfile

# ── unique email helpers ──────────────────────────────────────────────────────

def _uid() -> str:
    return uuid.uuid4().hex[:8]


# ── session-scoped fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="session")
def admin_token(db):
    """Create an admin user directly in the DB and return a JWT access token."""
    from app.core.security import create_access_token, create_refresh_token

    email = f"admin_{_uid()}@test.com"
    admin = User(
        full_name="Test Admin",
        email=email,
        password_hash=hash_password("AdminPass123!"),
        phone="0000000000",
        role="admin",
        status="active",
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    # Must set refresh_token — deps.py returns 401 if it is None
    refresh = create_refresh_token(str(admin.id), "admin")
    admin.refresh_token = refresh
    db.commit()

    token = create_access_token(str(admin.id), "admin")
    yield token

    # teardown
    db.delete(admin)
    db.commit()


@pytest.fixture(scope="session")
def manager_token(db):
    """Create a manager user directly in DB and return JWT access token."""
    from app.core.security import create_access_token, create_refresh_token

    # Ensure enum value exists even if local DB migration hasn't been applied yet.
    db.execute(text("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'manager'"))
    db.commit()

    email = f"manager_{_uid()}@test.com"
    manager = User(
        full_name="Test Manager",
        email=email,
        password_hash=hash_password("ManagerPass123!"),
        phone="0000000001",
        role="manager",
        status="active",
    )
    db.add(manager)
    db.commit()
    db.refresh(manager)

    refresh = create_refresh_token(str(manager.id), "manager")
    manager.refresh_token = refresh
    db.commit()

    token = create_access_token(str(manager.id), "manager")
    yield token

    db.delete(manager)
    db.commit()


@pytest.fixture(scope="session")
def client_credentials():
    return {
        "email": f"client_{_uid()}@test.com",
        "password": "ClientPass123!",
        "fullName": "Test Client",
        "phone": "1111111111",
    }


@pytest.fixture(scope="session")
def agent_credentials():
    return {
        "email": f"agent_{_uid()}@test.com",
        "password": "AgentPass123!",
        "fullName": "Test Agent",
        "phone": "2222222222",
    }


@pytest.fixture(scope="session")
def partner_credentials():
    return {
        "email": f"partner_{_uid()}@test.com",
        "password": "PartnerPass123!",
        "contactFirstName": "Test",
        "contactLastName": "Partner",
        "phone": "3333333333",
    }


@pytest.fixture(scope="session")
def http():
    """Plain HTTP client (no auth)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_client(admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    with TestClient(app, headers=headers) as c:
        yield c


@pytest.fixture(scope="session")
def manager_client(manager_token):
    headers = {"Authorization": f"Bearer {manager_token}"}
    with TestClient(app, headers=headers) as c:
        yield c


@pytest.fixture(scope="session")
def client_token_data(http, client_credentials):
    """Sign up a client and return the login token response dict."""
    r = http.post("/auth/client/signup", json={
        "fullName": client_credentials["fullName"],
        "email": client_credentials["email"],
        "password": client_credentials["password"],
        "phone": client_credentials["phone"],
    })
    assert r.status_code == 201, r.text

    r2 = http.post("/auth/login", json={
        "email": client_credentials["email"],
        "password": client_credentials["password"],
    })
    assert r2.status_code == 200, r2.text
    return r2.json()


@pytest.fixture(scope="session")
def client_http(client_token_data):
    headers = {"Authorization": f"Bearer {client_token_data['accessToken']}"}
    with TestClient(app, headers=headers) as c:
        yield c


@pytest.fixture(scope="session")
def agent_token_data(http, agent_credentials):
    r = http.post("/auth/agent/apply", json={
        "fullName": agent_credentials["fullName"],
        "email": agent_credentials["email"],
        "password": agent_credentials["password"],
        "phone": agent_credentials["phone"],
        "idNumber": "ID123456",
        "idType": "NATIONAL",
    })
    assert r.status_code == 201, r.text
    agent_id = r.json()["id"]

    # Admin must approve agent before login works (status=pending → active)
    # We activate directly via DB for test setup
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == agent_id).first()
        user.status = "active"
        db.commit()
    finally:
        db.close()

    r2 = http.post("/auth/login", json={
        "email": agent_credentials["email"],
        "password": agent_credentials["password"],
    })
    assert r2.status_code == 200, r2.text
    return r2.json()


@pytest.fixture(scope="session")
def agent_http(agent_token_data):
    headers = {"Authorization": f"Bearer {agent_token_data['accessToken']}"}
    with TestClient(app, headers=headers) as c:
        yield c


@pytest.fixture(scope="session")
def partner_token_data(http, partner_credentials):
    r = http.post("/auth/partner/signup", json={
        "contactFirstName": partner_credentials["contactFirstName"],
        "contactLastName": partner_credentials["contactLastName"],
        "email": partner_credentials["email"],
        "password": partner_credentials["password"],
        "phone": partner_credentials["phone"],
        "idNumber": "PID789",
        "idType": "PASSPORT",
        "businessName": "Test Tours Ltd",
    })
    assert r.status_code == 201, r.text
    partner_user_id = r.json()["id"]

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == partner_user_id).first()
        user.status = "active"
        db.commit()
    finally:
        db.close()

    r2 = http.post("/auth/login", json={
        "email": partner_credentials["email"],
        "password": partner_credentials["password"],
    })
    assert r2.status_code == 200, r2.text
    return r2.json()


@pytest.fixture(scope="session")
def partner_http(partner_token_data):
    headers = {"Authorization": f"Bearer {partner_token_data['accessToken']}"}
    with TestClient(app, headers=headers) as c:
        yield c


@pytest.fixture(scope="session")
def admin_user_id(admin_token):
    payload = decode_token(admin_token)
    return payload["sub"]


@pytest.fixture(scope="session")
def client_user_id(client_http):
    r = client_http.get("/users/me")
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture(scope="session")
def agent_user_id(agent_http):
    r = agent_http.get("/users/me")
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture(scope="session")
def partner_user_id(partner_http):
    r = partner_http.get("/users/me")
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture(scope="session")
def agent_profile_id(db, agent_user_id):
    profile = db.query(AgentProfile).filter(AgentProfile.user_id == agent_user_id).first()
    assert profile is not None
    return str(profile.id)


@pytest.fixture(scope="session")
def partner_profile_id(db, partner_user_id):
    profile = db.query(PartnerProfile).filter(PartnerProfile.user_id == partner_user_id).first()
    assert profile is not None
    return str(profile.id)
