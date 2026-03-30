"""
RBAC and ownership integration tests.

These tests are aligned with strict access-control behavior:
- Admin has global access.
- Agent/Partner/Client are constrained by role + ownership checks.
"""

import uuid
from datetime import datetime, timezone

import pytest


def _uid() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture(scope="module")
def catalog_ids(admin_client):
    cat = admin_client.post("/categories", json={"name": f"Cat {_uid()}", "slug": f"cat-{_uid()}"})
    assert cat.status_code == 201, cat.text
    cat_id = cat.json()["id"]

    svc = admin_client.post(
        "/services",
        json={"categoryId": cat_id, "name": f"Svc {_uid()}", "slug": f"svc-{_uid()}"},
    )
    assert svc.status_code == 201, svc.text

    return {"category_id": cat_id, "service_id": svc.json()["id"]}


@pytest.fixture(scope="module")
def partner_listing_id(partner_http, admin_client, partner_profile_id, catalog_ids):
    r = partner_http.post(
        "/listings",
        json={
            "partnerId": partner_profile_id,
            "categoryId": catalog_ids["category_id"],
            "serviceId": catalog_ids["service_id"],
            "title": "Matrix Listing",
            "description": "Owned by partner",
            "city": "Nairobi",
            "country": "Kenya",
            "priceFrom": 100,
            "pricingType": "per_person",
            "currency": "USD",
        },
    )
    assert r.status_code == 201, r.text
    listing_id = r.json()["id"]

    approve = admin_client.post(f"/listings/{listing_id}/approve")
    assert approve.status_code == 200, approve.text
    return listing_id


@pytest.fixture(scope="module")
def agent_quote_id(agent_http, partner_profile_id, agent_user_id):
    r = agent_http.post(
        "/quotes",
        json={
            "currency": "USD",
            "totalAmount": 900,
            "paymentType": "full",
            "agentId": agent_user_id,
            "partners": [{"partnerId": partner_profile_id, "PartnerAmount": 900}],
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.fixture(scope="module")
def owned_booking_id(client_http, client_user_id, agent_user_id, partner_profile_id):
    r = client_http.post(
        "/bookings",
        json={
            "clientId": client_user_id,
            "agentId": agent_user_id,
            "currency": "USD",
            "totalAmount": 500,
            "paymentType": "full",
            "costAtBooking": 500,
            "partners": [{"partnerId": partner_profile_id, "amount": 500}],
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.fixture(scope="module")
def completed_booking_id(client_http, agent_http, client_user_id, agent_user_id):
    create = client_http.post(
        "/bookings",
        json={
            "clientId": client_user_id,
            "agentId": agent_user_id,
            "currency": "USD",
            "totalAmount": 300,
            "paymentType": "full",
            "costAtBooking": 300,
        },
    )
    assert create.status_code == 201, create.text
    booking_id = create.json()["id"]
    done = agent_http.post(f"/bookings/{booking_id}/complete")
    assert done.status_code == 200, done.text
    return booking_id


@pytest.fixture(scope="module")
def payment_id(client_http, owned_booking_id):
    r = client_http.post(
        "/payments/initiate",
        json={"bookingId": owned_booking_id, "amount": 500, "currency": "USD", "provider": "stripe"},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture(scope="module")
def refund_id(client_http, owned_booking_id):
    r = client_http.post(
        "/refunds",
        json={"bookingId": owned_booking_id, "amount": 100, "reason": "Change of plans"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.fixture(scope="module")
def dispute_id(client_http, owned_booking_id):
    r = client_http.post(
        "/disputes",
        json={"bookingId": owned_booking_id, "reason": "Quality", "description": "Mismatch"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestAuthAndHealth:
    def test_health(self, http):
        r = http.get("/")
        assert r.status_code == 200

    def test_oauth_token_endpoint(self, http, client_credentials, client_token_data):
        # client_token_data fixture ensures the client account exists before OAuth token request.
        r = http.post(
            "/auth/token",
            data={"username": client_credentials["email"], "password": client_credentials["password"]},
        )
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


class TestAdminMatrix:
    def test_admin_can_list_clients_agents_partners(self, admin_client):
        assert admin_client.get("/clients").status_code == 200
        assert admin_client.get("/agents").status_code == 200
        assert admin_client.get("/partners").status_code == 200

    def test_admin_can_manage_catalog(self, admin_client):
        slug = f"rbac-cat-{_uid()}"
        create = admin_client.post("/categories", json={"name": "RBAC Cat", "slug": slug})
        assert create.status_code == 201
        cid = create.json()["id"]
        patch = admin_client.patch(f"/categories/{cid}", json={"name": "RBAC Cat 2"})
        assert patch.status_code == 200
        delete = admin_client.delete(f"/categories/{cid}")
        assert delete.status_code == 200

    def test_manager_can_create_service(self, manager_client, admin_client):
        cat = admin_client.post(
            "/categories",
            json={"name": f"Mgr Cat {_uid()}", "slug": f"mgr-cat-{_uid()}"},
        )
        assert cat.status_code == 201
        r = manager_client.post(
            "/services",
            json={"categoryId": cat.json()["id"], "name": "Mgr Service", "slug": f"mgr-svc-{_uid()}"},
        )
        assert r.status_code == 201

    def test_admin_can_create_and_deactivate_manager(self, admin_client, http):
        email = f"mgr-created-{_uid()}@test.com"
        password = "ManagerPass123!"

        create = admin_client.post(
            "/users/managers",
            json={"fullName": "Manager Created", "email": email, "password": password, "phone": "0710000000"},
        )
        assert create.status_code == 201, create.text
        manager_id = create.json()["id"]

        login = http.post("/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        access = login.json()["accessToken"]
        headers = {"Authorization": f"Bearer {access}"}

        assert http.get("/users/me", headers=headers).status_code == 200

        deactivate = admin_client.post(f"/users/managers/{manager_id}/deactivate")
        assert deactivate.status_code == 200, deactivate.text

        # Deactivation invalidates existing sessions by clearing refresh token.
        assert http.get("/users/me", headers=headers).status_code == 401


class TestRoleGates:
    def test_clients_and_agents_lists_are_admin_only(self, client_http, agent_http, partner_http, manager_client):
        # Clients and partners cannot list clients or agents
        assert client_http.get("/clients").status_code == 403
        assert partner_http.get("/clients").status_code == 403
        assert client_http.get("/agents").status_code == 403
        assert partner_http.get("/agents").status_code == 403

        # Agents CAN list clients (per spec — they need to look up client info)
        assert agent_http.get("/clients").status_code == 200
        # Agents cannot list agents (admin/manager only)
        assert agent_http.get("/agents").status_code == 403

        # Manager can list both
        assert manager_client.get("/clients").status_code == 200
        assert manager_client.get("/agents").status_code == 200

    def test_partner_listing_create_requires_own_profile(self, partner_http, catalog_ids, partner_profile_id):
        ok = partner_http.post(
            "/listings",
            json={
                "partnerId": partner_profile_id,
                "categoryId": catalog_ids["category_id"],
                "serviceId": catalog_ids["service_id"],
                "title": "Own Listing",
                "description": "ok",
                "city": "Nairobi",
                "country": "Kenya",
                "priceFrom": 150,
                "pricingType": "per_person",
                "currency": "USD",
            },
        )
        assert ok.status_code == 201

        not_own = partner_http.post(
            "/listings",
            json={
                "partnerId": str(uuid.uuid4()),
                "categoryId": catalog_ids["category_id"],
                "serviceId": catalog_ids["service_id"],
                "title": "Bad Listing",
                "description": "bad",
                "city": "Nairobi",
                "country": "Kenya",
                "priceFrom": 150,
                "pricingType": "per_person",
                "currency": "USD",
            },
        )
        assert not_own.status_code == 403

    def test_quotes_are_agent_admin_only(self, client_http, partner_http, agent_http, admin_client, agent_quote_id):
        assert client_http.get("/quotes").status_code == 403
        assert partner_http.get("/quotes").status_code == 403
        assert agent_http.get("/quotes").status_code == 200
        assert admin_client.get("/quotes").status_code == 200
        assert agent_http.get(f"/quotes/{agent_quote_id}").status_code == 200


class TestOwnershipFlows:
    def test_booking_visibility_and_completion(self, client_http, agent_http, partner_http, admin_client, owned_booking_id):
        assert client_http.get(f"/bookings/{owned_booking_id}").status_code == 200
        assert agent_http.get(f"/bookings/{owned_booking_id}").status_code == 200
        assert admin_client.get(f"/bookings/{owned_booking_id}").status_code == 200
        assert partner_http.get(f"/bookings/{owned_booking_id}").status_code == 403

        assert client_http.post(f"/bookings/{owned_booking_id}/complete").status_code == 403
        assert partner_http.post(f"/bookings/{owned_booking_id}/complete").status_code == 403
        assert agent_http.post(f"/bookings/{owned_booking_id}/complete").status_code == 200

    def test_booking_includes_guest_counts_and_special_notes(self, client_http, client_user_id, agent_user_id, partner_profile_id):
        create = client_http.post(
            "/bookings",
            json={
                "clientId": client_user_id,
                "agentId": agent_user_id,
                "currency": "USD",
                "totalAmount": 1200,
                "paymentType": "full",
                "costAtBooking": 1200,
                "partners": [{"partnerId": partner_profile_id, "amount": 1200}],
                "numberOfAdults": 2,
                "numberOfChildren": 1,
                "numberOfInfants": 1,
                "residency": "RESIDENT",
                "pets": True,
                "pickupLocation": "Airport",
                "destinationLocation": "Safari Lodge",
                "specialNotes": "Vegetarian meal plan",
            },
        )
        assert create.status_code == 201, create.text
        booking_id = create.json()["id"]

        get = client_http.get(f"/bookings/{booking_id}")
        assert get.status_code == 200, get.text
        booking_data = get.json()
        assert booking_data["number_of_adults"] == 2
        assert booking_data["number_of_children"] == 1
        assert booking_data["number_of_infants"] == 1
        assert booking_data["total_guests"] == 4
        assert booking_data["residency"] == "RESIDENT"
        assert booking_data["pets"] is True
        assert booking_data["pickup_location"] == "Airport"
        assert booking_data["destination_location"] == "Safari Lodge"
        assert booking_data["special_notes"] == "Vegetarian meal plan"

    def test_payments_scope(self, client_http, agent_http, partner_http, admin_client, owned_booking_id, payment_id):
        assert client_http.get(f"/payments/{payment_id}").status_code == 200
        assert agent_http.get(f"/payments/{payment_id}").status_code == 200
        assert admin_client.get(f"/payments/{payment_id}").status_code == 200
        assert partner_http.get(f"/payments/{payment_id}").status_code == 403

        # Partner cannot initiate payment
        r = partner_http.post(
            "/payments/initiate",
            json={"bookingId": owned_booking_id, "amount": 10, "currency": "USD", "provider": "stripe"},
        )
        assert r.status_code == 403

    def test_wallet_scope(self, partner_http, admin_client, client_http, partner_profile_id):
        assert partner_http.get(f"/wallets/{partner_profile_id}").status_code == 200
        assert partner_http.get(f"/wallets/{uuid.uuid4()}").status_code == 403
        assert admin_client.get(f"/wallets/{partner_profile_id}").status_code == 200
        assert client_http.get(f"/wallets/{partner_profile_id}").status_code == 403

    def test_refund_dispute_scope(self, client_http, agent_http, partner_http, admin_client, refund_id, dispute_id):
        assert client_http.get(f"/refunds/{refund_id}").status_code == 200
        assert agent_http.get(f"/refunds/{refund_id}").status_code == 200
        assert admin_client.get(f"/refunds/{refund_id}").status_code == 200
        assert partner_http.get(f"/refunds/{refund_id}").status_code == 403

        assert client_http.get(f"/disputes/{dispute_id}").status_code == 200
        assert agent_http.get(f"/disputes/{dispute_id}").status_code == 200
        assert admin_client.get(f"/disputes/{dispute_id}").status_code == 200
        assert partner_http.get(f"/disputes/{dispute_id}").status_code == 403

    def test_manager_can_approve_partner_and_listing(self, manager_client, partner_profile_id, partner_listing_id):
        assert manager_client.post(f"/partners/{partner_profile_id}/approve").status_code == 200
        assert manager_client.post(f"/listings/{partner_listing_id}/approve").status_code == 200

    def test_agent_cannot_update_dispute(self, agent_http, dispute_id):
        r = agent_http.patch(f"/disputes/{dispute_id}", json={"status": "under_review"})
        assert r.status_code == 403


class TestContractAndReviewMatrix:
    def test_contract_role_matrix(self, client_http, agent_http, partner_http, admin_client, manager_client, partner_profile_id, agent_user_id):
        now = datetime.now(timezone.utc).isoformat()

        c_client = client_http.post(
            "/contracts/client",
            json={"currency": "USD", "totalAmount": 100, "paymentType": "full"},
        )
        assert c_client.status_code == 201

        c_agent = manager_client.post(
            "/contracts/agent",
            json={"agentID": agent_user_id, "referenceID": f"A-{_uid()}", "fileurl": "https://x/a.pdf", "signedAt": now},
        )
        assert c_agent.status_code == 201

        c_partner = manager_client.post(
            "/contracts/partner",
            json={
                "partnerID": partner_profile_id,
                "referenceID": f"P-{_uid()}",
                "fileurl": "https://x/p.pdf",
                "signedAt": now,
            },
        )
        assert c_partner.status_code == 201

        # Role gate examples
        assert client_http.post(
            "/contracts/partner",
            json={
                "partnerID": partner_profile_id,
                "referenceID": f"BAD-{_uid()}",
                "fileurl": "https://x/bad.pdf",
                "signedAt": now,
            },
        ).status_code == 403
        assert partner_http.post(
            "/contracts/agent",
            json={"agentID": agent_user_id, "referenceID": f"BAD-{_uid()}", "fileurl": "https://x/bad.pdf", "signedAt": now},
        ).status_code == 403
        assert agent_http.post(
            "/contracts/agent",
            json={"agentID": agent_user_id, "referenceID": f"BAD2-{_uid()}", "fileurl": "https://x/bad2.pdf", "signedAt": now},
        ).status_code == 403
        assert admin_client.get("/contracts/clients").status_code == 200

    def test_reviews_matrix(self, client_http, agent_http, partner_http, admin_client, completed_booking_id):
        # list allowed for booking owner/agent/admin
        assert client_http.get(f"/bookings/{completed_booking_id}/reviews").status_code == 200
        assert agent_http.get(f"/bookings/{completed_booking_id}/reviews").status_code == 200
        assert admin_client.get(f"/bookings/{completed_booking_id}/reviews").status_code == 200
        assert partner_http.get(f"/bookings/{completed_booking_id}/reviews").status_code == 403

        r = client_http.post(
            f"/bookings/{completed_booking_id}/reviews",
            json={"rating": 5, "comment": "Great"},
        )
        assert r.status_code == 201

        bad = client_http.post(
            f"/bookings/{completed_booking_id}/reviews",
            json={"rating": 10, "comment": "Bad"},
        )
        assert bad.status_code == 400


class TestWithdrawalRequestWorkflow:
    def test_partner_large_withdrawal_creates_pending_request(self, db, partner_http, partner_profile_id):
        from app.models.payment import Wallet

        wallet = db.query(Wallet).filter(Wallet.partner_id == partner_profile_id).first()
        if wallet is None:
            wallet = Wallet(partner_id=partner_profile_id, escrow_balance=0, available_balance=1500, pending_balance=0)
        else:
            wallet.available_balance = 1500
        db.add(wallet)
        db.commit()

        r = partner_http.post(f"/wallets/{partner_profile_id}/withdraw", json={"amount": 1200})
        assert r.status_code == 200, r.text
        assert r.json()["message"] == "Withdrawal request submitted for approval"
        assert "requestId" in r.json()

    def test_admin_can_approve_withdrawal_request(self, db, admin_client, partner_profile_id):
        from app.models.payment import Wallet, WithdrawalRequest

        request = db.query(WithdrawalRequest).order_by(WithdrawalRequest.created_at.desc()).first()
        assert request is not None
        assert request.status == "pending"

        wallet = db.query(Wallet).filter(Wallet.id == request.wallet_id).first()
        assert wallet is not None
        starting_balance = float(wallet.available_balance)

        approve = admin_client.post(f"/payments/withdrawal-requests/{request.id}/approve")
        assert approve.status_code == 200, approve.text
        assert approve.json()["message"] == "Withdrawal request approved and processed"

        db.refresh(request)
        db.refresh(wallet)
        assert request.status == "approved"
        assert float(wallet.available_balance) == starting_balance - float(request.amount)

    def test_admin_can_reject_withdrawal_request(self, db, admin_client, partner_profile_id):
        from app.models.payment import Wallet, WithdrawalRequest
        from app.models.profile import PartnerProfile

        wallet = db.query(Wallet).filter(Wallet.partner_id == partner_profile_id).first()
        assert wallet is not None
        wallet.available_balance = 2000
        db.add(wallet)
        db.commit()

        partner_profile = db.query(PartnerProfile).filter(PartnerProfile.id == partner_profile_id).first()
        assert partner_profile is not None

        request = WithdrawalRequest(
            wallet_id=wallet.id,
            amount=1500,
            requested_by=partner_profile.user_id,
        )
        db.add(request)
        db.commit()
        db.refresh(request)

        reject = admin_client.post(
            f"/payments/withdrawal-requests/{request.id}/reject",
            json={"review_note": "Request denied for testing"},
        )
        assert reject.status_code == 200, reject.text
        assert reject.json()["message"] == "Withdrawal request rejected"

        db.refresh(request)
        assert request.status == "rejected"
