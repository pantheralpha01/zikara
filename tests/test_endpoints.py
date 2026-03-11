"""
Integration tests for all API endpoints.

Requires the server to be running at http://localhost:8000.
Run with:  pytest tests/ -v
"""

import uuid
import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def uid() -> str:
    return uuid.uuid4().hex[:8]


# =============================================================================
# AUTH
# =============================================================================

class TestAuth:
    def test_client_signup_success(self, http):
        r = http.post("/auth/client/signup", json={
            "fullName": "Signup Test",
            "email": f"signup_{uid()}@test.com",
            "password": "Pass1234!",
            "phone": "0987654321",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["role"] == "client"
        assert data["status"] == "active"

    def test_client_signup_duplicate_email(self, http):
        email = f"dup_{uid()}@test.com"
        # Register once
        r1 = http.post("/auth/client/signup", json={
            "fullName": "First",
            "email": email,
            "password": "Pass1234!",
            "phone": "0000000001",
        })
        assert r1.status_code == 201
        # Register again with same email
        r2 = http.post("/auth/client/signup", json={
            "fullName": "Second",
            "email": email,
            "password": "Pass1234!",
            "phone": "0000000002",
        })
        assert r2.status_code == 409

    def test_login_success(self, http):
        email = f"login_{uid()}@test.com"
        password = "LoginPass123!"
        http.post("/auth/client/signup", json={
            "fullName": "Login Test",
            "email": email,
            "password": password,
            "phone": "9999999999",
        })
        r = http.post("/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200
        data = r.json()
        assert "accessToken" in data
        assert "refreshToken" in data

    def test_login_wrong_password(self, http):
        email = f"wrongpw_{uid()}@test.com"
        http.post("/auth/client/signup", json={
            "fullName": "WrongPW",
            "email": email,
            "password": "CorrectPass123!",
            "phone": "8888888888",
        })
        r = http.post("/auth/login", json={"email": email, "password": "WrongPass!"})
        assert r.status_code == 401

    def test_refresh_token(self, http):
        email = f"refresh_{uid()}@test.com"
        password = "RefreshPass123!"
        http.post("/auth/client/signup", json={
            "fullName": "Refresh Test",
            "email": email,
            "password": password,
            "phone": "7777777777",
        })
        login = http.post("/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200
        refresh_token = login.json()["refreshToken"]

        r = http.post("/auth/refresh", json={"refreshToken": refresh_token})
        assert r.status_code == 200
        assert "accessToken" in r.json()

    def test_refresh_invalid_token(self, http):
        r = http.post("/auth/refresh", json={"refreshToken": "not.a.valid.token"})
        assert r.status_code == 401

    def test_logout(self, http):
        email = f"logout_{uid()}@test.com"
        password = "LogoutPass123!"
        http.post("/auth/client/signup", json={
            "fullName": "Logout Test",
            "email": email,
            "password": password,
            "phone": "6666666666",
        })
        login = http.post("/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200
        access_token = login.json()["accessToken"]

        headers = {"Authorization": f"Bearer {access_token}"}
        r = http.post("/auth/logout", headers=headers)
        assert r.status_code == 200

    def test_agent_apply(self, http):
        r = http.post("/auth/agent/apply", json={
            "fullName": "Agent Applicant",
            "email": f"agent_{uid()}@test.com",
            "password": "Pass1234!",
            "phone": "1234567890",
            "idNumber": "NEWID001",
            "idType": "PASSPORT",
            "city": "Nairobi",
            "country": "Kenya",
        })
        assert r.status_code == 201
        assert r.json()["role"] == "agent"
        assert r.json()["status"] == "pending"

    def test_partner_signup(self, http):
        r = http.post("/auth/partner/signup", json={
            "contactFirstName": "New",
            "contactLastName": "Partner",
            "email": f"partner_{uid()}@test.com",
            "password": "Pass1234!",
            "phone": "0987654321",
            "idNumber": "PID001",
            "idType": "NATIONAL",
            "businessName": "New Biz",
        })
        assert r.status_code == 201
        assert r.json()["role"] == "partner"


# =============================================================================
# USERS  (/users/me)
# =============================================================================

class TestUsers:
    def test_get_me(self, client_http):
        r = client_http.get("/users/me")
        assert r.status_code == 200
        assert "email" in r.json()

    def test_update_me(self, client_http):
        r = client_http.patch("/users/me", json={"full_name": "Updated Name"})
        assert r.status_code == 200
        assert r.json()["full_name"] == "Updated Name"

    def test_get_me_unauthenticated(self, http):
        r = http.get("/users/me")
        assert r.status_code == 401

    def test_delete_me_requires_auth(self, http):
        r = http.delete("/users/me")
        assert r.status_code == 401


# =============================================================================
# CLIENTS
# =============================================================================

class TestClients:
    def test_list_clients_as_admin(self, admin_client):
        r = admin_client.get("/clients")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_clients_as_non_admin(self, client_http):
        r = client_http.get("/clients")
        assert r.status_code == 403

    def test_get_client_not_found(self, admin_client):
        r = admin_client.get(f"/clients/{uuid.uuid4()}")
        assert r.status_code == 404


# =============================================================================
# AGENTS
# =============================================================================

class TestAgents:
    def test_list_agents_as_admin(self, admin_client):
        r = admin_client.get("/agents")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_agents_non_admin_forbidden(self, client_http):
        r = client_http.get("/agents")
        assert r.status_code == 403

    def test_get_agent_not_found(self, admin_client):
        r = admin_client.get(f"/agents/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_approve_agent(self, admin_client, agent_token_data, db):
        # Find the agent profile
        from app.models.profile import AgentProfile
        from app.models.user import User as UserModel
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            # Get a pending agent profile to approve
            agent_profile = sess.query(AgentProfile).first()
            if agent_profile:
                r = admin_client.post(f"/agents/{agent_profile.id}/approve")
                assert r.status_code == 200
        finally:
            sess.close()

    def test_suspend_agent(self, admin_client, db):
        from app.models.profile import AgentProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            agent_profile = sess.query(AgentProfile).first()
            if agent_profile:
                r = admin_client.post(f"/agents/{agent_profile.id}/suspend")
                assert r.status_code == 200
        finally:
            sess.close()


# =============================================================================
# PARTNERS
# =============================================================================

class TestPartners:
    def test_list_partners_as_admin(self, admin_client):
        r = admin_client.get("/partners")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "items" in data

    def test_list_partners_non_admin_forbidden(self, client_http):
        r = client_http.get("/partners")
        assert r.status_code == 403

    def test_get_partner_not_found(self, admin_client):
        r = admin_client.get(f"/partners/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_approve_partner(self, admin_client, db):
        from app.models.profile import PartnerProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            partner_profile = sess.query(PartnerProfile).first()
            if partner_profile:
                r = admin_client.post(f"/partners/{partner_profile.id}/approve")
                assert r.status_code == 200
        finally:
            sess.close()

    def test_reject_partner(self, admin_client, db):
        from app.models.profile import PartnerProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            partner_profile = sess.query(PartnerProfile).first()
            if partner_profile:
                r = admin_client.post(f"/partners/{partner_profile.id}/reject")
                assert r.status_code == 200
        finally:
            sess.close()

    def test_partner_wallet(self, admin_client, db):
        from app.models.profile import PartnerProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            partner_profile = sess.query(PartnerProfile).first()
            if partner_profile:
                r = admin_client.get(f"/partners/{partner_profile.id}/wallet")
                assert r.status_code == 200
        finally:
            sess.close()


# =============================================================================
# CATEGORIES
# =============================================================================

class TestCategories:
    @pytest.fixture(scope="class")
    def category_id(self, admin_client):
        slug = f"test-cat-{uid()}"
        r = admin_client.post("/categories", json={
            "name": "Test Category",
            "slug": slug,
            "isActive": True,
            "attributesSchema": [],
        })
        assert r.status_code == 201
        return r.json()["id"]

    def test_create_category(self, admin_client):
        r = admin_client.post("/categories", json={
            "name": "Another Category",
            "slug": f"another-{uid()}",
            "isActive": True,
        })
        assert r.status_code == 201
        assert r.json()["slug"].startswith("another-")

    def test_create_category_duplicate_slug(self, admin_client, category_id):
        # Get slug from a prior category
        r = admin_client.get("/categories")
        items = r.json()["items"]
        if items:
            slug = items[0]["slug"]
            r2 = admin_client.post("/categories", json={"name": "Dup", "slug": slug})
            assert r2.status_code == 409

    def test_create_category_non_admin(self, client_http):
        r = client_http.post("/categories", json={"name": "X", "slug": f"x-{uid()}"})
        assert r.status_code == 403

    def test_list_categories(self, client_http):
        r = client_http.get("/categories")
        assert r.status_code == 200
        assert "items" in r.json()

    def test_update_category(self, admin_client, category_id):
        r = admin_client.patch(f"/categories/{category_id}", json={"name": "Updated Cat"})
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Cat"

    def test_update_category_not_found(self, admin_client):
        r = admin_client.patch(f"/categories/{uuid.uuid4()}", json={"name": "X"})
        assert r.status_code == 404

    def test_delete_category(self, admin_client):
        r = admin_client.post("/categories", json={"name": "To Delete", "slug": f"del-{uid()}"})
        assert r.status_code == 201
        cat_id = r.json()["id"]
        r2 = admin_client.delete(f"/categories/{cat_id}")
        assert r2.status_code == 200

    def test_delete_category_not_found(self, admin_client):
        r = admin_client.delete(f"/categories/{uuid.uuid4()}")
        assert r.status_code == 404


# =============================================================================
# SERVICES
# =============================================================================

class TestServices:
    @pytest.fixture(scope="class")
    def category_and_service(self, admin_client):
        cat = admin_client.post("/categories", json={
            "name": "Svc Test Cat",
            "slug": f"svc-cat-{uid()}",
        })
        assert cat.status_code == 201
        cat_id = cat.json()["id"]

        svc = admin_client.post("/services", json={
            "categoryId": cat_id,
            "name": "Test Service",
            "slug": f"test-svc-{uid()}",
            "isActive": True,
        })
        assert svc.status_code == 201
        return {"categoryId": cat_id, "serviceId": svc.json()["id"]}

    def test_create_service(self, admin_client):
        cat = admin_client.post("/categories", json={
            "name": "Cat for Svc",
            "slug": f"cat4svc-{uid()}",
        })
        assert cat.status_code == 201
        r = admin_client.post("/services", json={
            "categoryId": cat.json()["id"],
            "name": "My Service",
            "slug": f"my-svc-{uid()}",
        })
        assert r.status_code == 201

    def test_create_service_non_admin(self, client_http):
        r = client_http.post("/services", json={
            "categoryId": str(uuid.uuid4()),
            "name": "X",
            "slug": f"x-{uid()}",
        })
        assert r.status_code == 403

    def test_list_services(self, client_http):
        r = client_http.get("/services")
        assert r.status_code == 200
        assert "items" in r.json()

    def test_update_service(self, admin_client, category_and_service):
        svc_id = category_and_service["serviceId"]
        r = admin_client.patch(f"/services/{svc_id}", json={"name": "Updated Service"})
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Service"

    def test_update_service_not_found(self, admin_client):
        r = admin_client.patch(f"/services/{uuid.uuid4()}", json={"name": "X"})
        assert r.status_code == 404


# =============================================================================
# LISTINGS
# =============================================================================

class TestListings:
    @pytest.fixture(scope="class")
    def listing_data(self, admin_client, partner_http, db):
        from app.models.profile import PartnerProfile
        from app.db.session import SessionLocal

        # Ensure partner is active and get their profile ID
        sess = SessionLocal()
        try:
            partner_profile = sess.query(PartnerProfile).first()
            assert partner_profile, "No partner profile found"
            partner_id = str(partner_profile.id)
        finally:
            sess.close()

        # Create category
        cat = admin_client.post("/categories", json={
            "name": "Listing Cat",
            "slug": f"list-cat-{uid()}",
        })
        assert cat.status_code == 201
        cat_id = cat.json()["id"]

        # Create listing as partner
        r = partner_http.post("/listings", json={
            "partnerId": partner_id,
            "categoryId": cat_id,
            "title": "Safari Tour",
            "description": "A great safari",
            "city": "Nairobi",
            "country": "Kenya",
            "priceFrom": 500.0,
            "pricingType": "per_person",
            "currency": "USD",
        })
        assert r.status_code == 201
        return {"listingId": r.json()["id"], "categoryId": cat_id}

    def test_create_listing(self, partner_http, admin_client, db):
        from app.models.profile import PartnerProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            partner_profile = sess.query(PartnerProfile).first()
            assert partner_profile
            partner_id = str(partner_profile.id)
        finally:
            sess.close()

        cat = admin_client.post("/categories", json={
            "name": "L2 Cat",
            "slug": f"l2cat-{uid()}",
        })
        assert cat.status_code == 201

        r = partner_http.post("/listings", json={
            "partnerId": partner_id,
            "categoryId": cat.json()["id"],
            "title": "Beach Tour",
            "description": "Beach fun",
            "city": "Mombasa",
            "country": "Kenya",
            "priceFrom": 200.0,
            "pricingType": "per_person",
            "currency": "USD",
        })
        assert r.status_code == 201

    def test_list_listings(self, client_http):
        r = client_http.get("/listings")
        assert r.status_code == 200
        assert "items" in r.json()

    def test_approve_listing(self, admin_client, listing_data):
        r = admin_client.post(f"/listings/{listing_data['listingId']}/approve")
        assert r.status_code == 200

    def test_reject_listing(self, admin_client, listing_data):
        r = admin_client.post(f"/listings/{listing_data['listingId']}/reject")
        assert r.status_code == 200

    def test_approve_listing_not_found(self, admin_client):
        r = admin_client.post(f"/listings/{uuid.uuid4()}/approve")
        assert r.status_code == 404


# =============================================================================
# QUOTES
# =============================================================================

class TestQuotes:
    @pytest.fixture(scope="class")
    def quote_id(self, client_http, db):
        from app.models.profile import AgentProfile, PartnerProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            agent = sess.query(AgentProfile).first()
            partner = sess.query(PartnerProfile).first()
            agent_id = str(agent.user_id) if agent else None
            partner_id = str(partner.id) if partner else None
        finally:
            sess.close()

        r = client_http.post("/quotes", json={
            "currency": "USD",
            "totalAmount": 1000.0,
            "paymentType": "full",
            "partners": [{"partnerId": partner_id, "PartnerAmount": 1000}] if partner_id else [],
            "agentId": agent_id,
        })
        assert r.status_code == 201
        return r.json()["id"]

    def test_create_quote(self, quote_id):
        assert quote_id is not None

    def test_list_quotes(self, client_http):
        r = client_http.get("/quotes")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_quote(self, client_http, quote_id):
        r = client_http.get(f"/quotes/{quote_id}")
        assert r.status_code == 200
        assert r.json()["id"] == quote_id

    def test_get_quote_not_found(self, client_http):
        r = client_http.get(f"/quotes/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_delete_quote(self, client_http):
        from app.models.profile import PartnerProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            partner = sess.query(PartnerProfile).first()
            partner_id = str(partner.id) if partner else None
        finally:
            sess.close()

        r = client_http.post("/quotes", json={
            "currency": "USD",
            "totalAmount": 200.0,
            "paymentType": "full",
            "partners": [{"partnerId": partner_id, "PartnerAmount": 200}] if partner_id else [],
        })
        assert r.status_code == 201
        qid = r.json()["id"]
        r2 = client_http.delete(f"/quotes/{qid}")
        assert r2.status_code == 200


# =============================================================================
# CONTRACTS
# =============================================================================

class TestContracts:
    @pytest.fixture(scope="class")
    def client_contract_id(self, client_http, db):
        from app.models.profile import AgentProfile, PartnerProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            agent = sess.query(AgentProfile).first()
            partner = sess.query(PartnerProfile).first()
            agent_id = str(agent.user_id) if agent else None
            partner_id = str(partner.id) if partner else None
        finally:
            sess.close()

        r = client_http.post("/contracts/client", json={
            "currency": "USD",
            "totalAmount": 1500.0,
            "paymentType": "split",
            "agentId": agent_id,
            "partners": [{"partnerId": partner_id, "PartnerAmount": 1500}] if partner_id else [],
        })
        assert r.status_code == 201
        return r.json()["id"]

    @pytest.fixture(scope="class")
    def partner_contract_id(self, client_http, db):
        from app.models.profile import PartnerProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            partner = sess.query(PartnerProfile).first()
            partner_id = str(partner.id)
        finally:
            sess.close()

        from datetime import datetime, timezone
        r = client_http.post("/contracts/partner", json={
            "partnerID": partner_id,
            "referenceID": f"REF-{uid()}",
            "fileurl": "https://example.com/contract.pdf",
            "signedAt": datetime.now(timezone.utc).isoformat(),
        })
        assert r.status_code == 201
        return r.json()["id"]

    @pytest.fixture(scope="class")
    def agent_contract_id(self, client_http, db):
        from app.models.profile import AgentProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            agent = sess.query(AgentProfile).first()
            agent_id = str(agent.user_id)
        finally:
            sess.close()

        from datetime import datetime, timezone
        r = client_http.post("/contracts/agent", json={
            "agentID": agent_id,
            "referenceID": f"REF-{uid()}",
            "fileurl": "https://example.com/agent-contract.pdf",
            "signedAt": datetime.now(timezone.utc).isoformat(),
        })
        assert r.status_code == 201
        return r.json()["id"]

    # Client contracts
    def test_list_client_contracts(self, client_http):
        r = client_http.get("/contracts/clients")
        assert r.status_code == 200

    def test_get_client_contract(self, client_http, client_contract_id):
        r = client_http.get(f"/contracts/clients/{client_contract_id}")
        assert r.status_code == 200

    def test_update_client_contract(self, client_http, client_contract_id):
        r = client_http.patch(f"/contracts/clients/{client_contract_id}", json={
            "customer_name": "Updated Customer"
        })
        assert r.status_code == 200

    def test_delete_client_contract(self, client_http, db):
        r = client_http.post("/contracts/client", json={
            "currency": "USD",
            "totalAmount": 100.0,
            "paymentType": "full",
        })
        assert r.status_code == 201
        cid = r.json()["id"]
        r2 = client_http.delete(f"/contracts/clients/{cid}")
        assert r2.status_code == 200

    # Partner contracts
    def test_list_partner_contracts(self, client_http):
        r = client_http.get("/contracts/partners")
        assert r.status_code == 200

    def test_get_partner_contract(self, client_http, partner_contract_id):
        r = client_http.get(f"/contracts/partners/{partner_contract_id}")
        assert r.status_code == 200

    def test_update_partner_contract(self, client_http, partner_contract_id):
        r = client_http.patch(f"/contracts/partners/{partner_contract_id}", json={
            "reference_id": f"REF-UPDATED-{uid()}"
        })
        assert r.status_code == 200

    # Agent contracts
    def test_list_agent_contracts(self, client_http):
        r = client_http.get("/contracts/agents")
        assert r.status_code == 200

    def test_get_agent_contract(self, client_http, agent_contract_id):
        r = client_http.get(f"/contracts/agents/{agent_contract_id}")
        assert r.status_code == 200

    def test_update_agent_contract(self, client_http, agent_contract_id):
        r = client_http.patch(f"/contracts/agents/{agent_contract_id}", json={
            "reference_id": f"REF-AG-{uid()}"
        })
        assert r.status_code == 200

    def test_get_contract_not_found(self, client_http):
        r = client_http.get(f"/contracts/clients/{uuid.uuid4()}")
        assert r.status_code == 404


# =============================================================================
# BOOKINGS
# =============================================================================

class TestBookings:
    @pytest.fixture(scope="class")
    def booking_id(self, client_http, db):
        from app.models.user import User as UserModel
        from app.models.profile import AgentProfile, PartnerProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            client_user = sess.query(UserModel).filter(UserModel.role == "client").first()
            agent = sess.query(AgentProfile).first()
            partner = sess.query(PartnerProfile).first()
            client_id = str(client_user.id) if client_user else None
            agent_id = str(agent.user_id) if agent else None
            partner_id = str(partner.id) if partner else None
        finally:
            sess.close()

        r = client_http.post("/bookings", json={
            "clientId": client_id,
            "agentId": agent_id,
            "currency": "USD",
            "totalAmount": 800.0,
            "paymentType": "full",
            "costAtBooking": 800.0,
            "status": "confirmed",
            "partners": [{"partnerId": partner_id, "amount": 800}] if partner_id else [],
        })
        assert r.status_code == 201
        return r.json()["id"]

    def test_create_booking(self, booking_id):
        assert booking_id is not None

    def test_list_bookings(self, client_http):
        r = client_http.get("/bookings")
        assert r.status_code == 200
        assert "items" in r.json()

    def test_booking_calendar(self, client_http):
        r = client_http.get("/bookings/calendar")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_booking(self, client_http, booking_id):
        r = client_http.get(f"/bookings/{booking_id}")
        assert r.status_code == 200
        assert r.json()["id"] == booking_id

    def test_update_booking_status(self, client_http, booking_id):
        r = client_http.patch(f"/bookings/{booking_id}", json={"status": "confirmed"})
        assert r.status_code == 200

    def test_get_booking_not_found(self, client_http):
        r = client_http.get(f"/bookings/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_complete_booking(self, agent_http, booking_id):
        r = agent_http.post(f"/bookings/{booking_id}/complete")
        assert r.status_code == 200

    def test_complete_booking_requires_agent(self, client_http, booking_id):
        r = client_http.post(f"/bookings/{booking_id}/complete")
        assert r.status_code == 403

    def test_delete_booking(self, client_http, db):
        from app.models.user import User as UserModel
        from app.models.profile import AgentProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            client_user = sess.query(UserModel).filter(UserModel.role == "client").first()
            agent = sess.query(AgentProfile).first()
            client_id = str(client_user.id)
            agent_id = str(agent.user_id)
        finally:
            sess.close()

        r = client_http.post("/bookings", json={
            "clientId": client_id,
            "agentId": agent_id,
            "currency": "USD",
            "totalAmount": 100.0,
            "paymentType": "full",
            "costAtBooking": 100.0,
            "status": "confirmed",
        })
        assert r.status_code == 201
        bid = r.json()["id"]
        r2 = client_http.delete(f"/bookings/{bid}")
        assert r2.status_code == 200


# =============================================================================
# PAYMENTS
# =============================================================================

class TestPayments:
    @pytest.fixture(scope="class")
    def payment_id(self, client_http, booking_id):
        r = client_http.post("/payments/initiate", json={
            "bookingId": booking_id,
            "amount": 800.0,
            "currency": "USD",
            "provider": "stripe",
        })
        assert r.status_code == 200
        return r.json()["id"]

    @pytest.fixture(scope="class")
    def booking_id(self, client_http, db):
        from app.models.user import User as UserModel
        from app.models.profile import AgentProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            client_user = sess.query(UserModel).filter(UserModel.role == "client").first()
            agent = sess.query(AgentProfile).first()
            client_id = str(client_user.id)
            agent_id = str(agent.user_id)
        finally:
            sess.close()

        r = client_http.post("/bookings", json={
            "clientId": client_id,
            "agentId": agent_id,
            "currency": "USD",
            "totalAmount": 800.0,
            "paymentType": "full",
            "costAtBooking": 800.0,
            "status": "confirmed",
        })
        assert r.status_code == 201
        return r.json()["id"]

    def test_initiate_payment(self, payment_id):
        assert payment_id is not None

    def test_list_payments(self, client_http):
        r = client_http.get("/payments/list")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_payment(self, client_http, payment_id):
        r = client_http.get(f"/payments/{payment_id}")
        assert r.status_code == 200

    def test_get_payment_not_found(self, client_http):
        r = client_http.get(f"/payments/{uuid.uuid4()}")
        assert r.status_code == 404


# =============================================================================
# WALLETS
# =============================================================================

class TestWallets:
    def test_get_wallet_no_wallet(self, client_http, db):
        from app.models.profile import PartnerProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            partner = sess.query(PartnerProfile).first()
            partner_id = str(partner.id) if partner else str(uuid.uuid4())
        finally:
            sess.close()

        r = client_http.get(f"/wallets/{partner_id}")
        assert r.status_code == 200

    def test_withdraw_wallet_not_found(self, client_http):
        r = client_http.post(f"/wallets/{uuid.uuid4()}/withdraw", json={"amount": 10.0})
        assert r.status_code == 404

    def test_withdraw_invalid_amount(self, client_http, db):
        from app.models.payment import Wallet
        from app.models.profile import PartnerProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            partner = sess.query(PartnerProfile).first()
            if partner:
                # Get or create wallet (partner_id has a unique constraint)
                wallet = sess.query(Wallet).filter(Wallet.partner_id == partner.id).first()
                if not wallet:
                    wallet = Wallet(partner_id=partner.id, escrow_balance=0, available_balance=0)
                    sess.add(wallet)
                    sess.commit()
                partner_id = str(partner.id)
        finally:
            sess.close()

        r = client_http.post(f"/wallets/{partner_id}/withdraw", json={"amount": -5.0})
        assert r.status_code == 400


# =============================================================================
# REFUNDS
# =============================================================================

class TestRefunds:
    @pytest.fixture(scope="class")
    def booking_and_refund(self, client_http, db):
        from app.models.user import User as UserModel
        from app.models.profile import AgentProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            client_user = sess.query(UserModel).filter(UserModel.role == "client").first()
            agent = sess.query(AgentProfile).first()
            client_id = str(client_user.id)
            agent_id = str(agent.user_id)
        finally:
            sess.close()

        booking = client_http.post("/bookings", json={
            "clientId": client_id,
            "agentId": agent_id,
            "currency": "USD",
            "totalAmount": 300.0,
            "paymentType": "full",
            "costAtBooking": 300.0,
            "status": "confirmed",
        })
        assert booking.status_code == 201
        booking_id = booking.json()["id"]

        refund = client_http.post("/refunds", json={
            "bookingId": booking_id,
            "amount": 150.0,
            "reason": "Service not as described",
        })
        assert refund.status_code == 201
        return {"bookingId": booking_id, "refundId": refund.json()["id"]}

    def test_create_refund(self, booking_and_refund):
        assert booking_and_refund["refundId"] is not None

    def test_list_refunds(self, client_http):
        r = client_http.get("/refunds")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_refund(self, client_http, booking_and_refund):
        r = client_http.get(f"/refunds/{booking_and_refund['refundId']}")
        assert r.status_code == 200

    def test_update_refund(self, client_http, booking_and_refund):
        r = client_http.patch(f"/refunds/{booking_and_refund['refundId']}", json={"status": "approved"})
        assert r.status_code == 200

    def test_get_refund_not_found(self, client_http):
        r = client_http.get(f"/refunds/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_delete_refund(self, client_http, db):
        from app.models.user import User as UserModel
        from app.models.profile import AgentProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            client_user = sess.query(UserModel).filter(UserModel.role == "client").first()
            agent = sess.query(AgentProfile).first()
            client_id = str(client_user.id)
            agent_id = str(agent.user_id)
        finally:
            sess.close()

        booking = client_http.post("/bookings", json={
            "clientId": client_id,
            "agentId": agent_id,
            "currency": "USD",
            "totalAmount": 100.0,
            "paymentType": "full",
            "costAtBooking": 100.0,
            "status": "confirmed",
        })
        bid = booking.json()["id"]

        r = client_http.post("/refunds", json={
            "bookingId": bid,
            "amount": 50.0,
            "reason": "Cancelled",
        })
        assert r.status_code == 201
        rid = r.json()["id"]
        r2 = client_http.delete(f"/refunds/{rid}")
        assert r2.status_code == 200


# =============================================================================
# DISPUTES
# =============================================================================

class TestDisputes:
    @pytest.fixture(scope="class")
    def dispute_id(self, client_http, db):
        from app.models.user import User as UserModel
        from app.models.profile import AgentProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            client_user = sess.query(UserModel).filter(UserModel.role == "client").first()
            agent = sess.query(AgentProfile).first()
            client_id = str(client_user.id)
            agent_id = str(agent.user_id)
        finally:
            sess.close()

        booking = client_http.post("/bookings", json={
            "clientId": client_id,
            "agentId": agent_id,
            "currency": "USD",
            "totalAmount": 500.0,
            "paymentType": "full",
            "costAtBooking": 500.0,
            "status": "confirmed",
        })
        assert booking.status_code == 201
        bid = booking.json()["id"]

        r = client_http.post("/disputes", json={
            "bookingId": bid,
            "reason": "Overcharged",
            "description": "Was charged more than agreed",
        })
        assert r.status_code == 201
        return r.json()["id"]

    def test_create_dispute(self, dispute_id):
        assert dispute_id is not None

    def test_list_disputes(self, client_http):
        r = client_http.get("/disputes")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_dispute(self, client_http, dispute_id):
        r = client_http.get(f"/disputes/{dispute_id}")
        assert r.status_code == 200

    def test_update_dispute(self, client_http, dispute_id):
        r = client_http.patch(f"/disputes/{dispute_id}", json={"status": "under_review"})
        assert r.status_code == 200

    def test_get_dispute_not_found(self, client_http):
        r = client_http.get(f"/disputes/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_delete_dispute(self, client_http, db):
        from app.models.user import User as UserModel
        from app.models.profile import AgentProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            client_user = sess.query(UserModel).filter(UserModel.role == "client").first()
            agent = sess.query(AgentProfile).first()
            client_id = str(client_user.id)
            agent_id = str(agent.user_id)
        finally:
            sess.close()

        booking = client_http.post("/bookings", json={
            "clientId": client_id,
            "agentId": agent_id,
            "currency": "USD",
            "totalAmount": 100.0,
            "paymentType": "full",
            "costAtBooking": 100.0,
            "status": "confirmed",
        })
        bid = booking.json()["id"]

        r = client_http.post("/disputes", json={
            "bookingId": bid,
            "reason": "Test",
            "description": "Test dispute",
        })
        assert r.status_code == 201
        did = r.json()["id"]
        r2 = client_http.delete(f"/disputes/{did}")
        assert r2.status_code == 200


# =============================================================================
# REVIEWS
# =============================================================================

class TestReviews:
    @pytest.fixture(scope="class")
    def completed_booking_id(self, client_http, agent_http, db):
        from app.models.user import User as UserModel
        from app.models.profile import AgentProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            client_user = sess.query(UserModel).filter(UserModel.role == "client").first()
            agent = sess.query(AgentProfile).first()
            client_id = str(client_user.id)
            agent_id = str(agent.user_id)
        finally:
            sess.close()

        booking = client_http.post("/bookings", json={
            "clientId": client_id,
            "agentId": agent_id,
            "currency": "USD",
            "totalAmount": 200.0,
            "paymentType": "full",
            "costAtBooking": 200.0,
            "status": "confirmed",
        })
        assert booking.status_code == 201
        bid = booking.json()["id"]

        # Mark as completed via agent
        r = agent_http.post(f"/bookings/{bid}/complete")
        assert r.status_code == 200

        return bid

    def test_list_reviews_empty(self, client_http, completed_booking_id):
        r = client_http.get(f"/bookings/{completed_booking_id}/reviews")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_review(self, client_http, completed_booking_id):
        r = client_http.post(f"/bookings/{completed_booking_id}/reviews", json={
            "rating": 5,
            "comment": "Excellent service!",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["rating"] == 5

    def test_create_review_on_non_completed_booking(self, client_http, db):
        from app.models.user import User as UserModel
        from app.models.profile import AgentProfile
        from app.db.session import SessionLocal

        sess = SessionLocal()
        try:
            client_user = sess.query(UserModel).filter(UserModel.role == "client").first()
            agent = sess.query(AgentProfile).first()
            client_id = str(client_user.id)
            agent_id = str(agent.user_id)
        finally:
            sess.close()

        booking = client_http.post("/bookings", json={
            "clientId": client_id,
            "agentId": agent_id,
            "currency": "USD",
            "totalAmount": 100.0,
            "paymentType": "full",
            "costAtBooking": 100.0,
            "status": "confirmed",
        })
        bid = booking.json()["id"]

        r = client_http.post(f"/bookings/{bid}/reviews", json={
            "rating": 3,
            "comment": "Should fail",
        })
        assert r.status_code == 400

    def test_create_review_invalid_rating(self, client_http, completed_booking_id):
        r = client_http.post(f"/bookings/{completed_booking_id}/reviews", json={
            "rating": 10,
            "comment": "Too high",
        })
        assert r.status_code == 400

    def test_reviews_booking_not_found(self, client_http):
        r = client_http.get(f"/bookings/{uuid.uuid4()}/reviews")
        # Returns empty list or 404 depending on implementation
        assert r.status_code in (200, 404)
