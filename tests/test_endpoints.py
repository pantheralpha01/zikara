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
            "status": "confirmed",
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
            "status": "confirmed",
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


class TestRoleGates:
    def test_clients_and_agents_lists_are_admin_only(self, client_http, agent_http, partner_http):
        assert client_http.get("/clients").status_code == 403
        assert agent_http.get("/clients").status_code == 403
        assert partner_http.get("/clients").status_code == 403

        assert client_http.get("/agents").status_code == 403
        assert agent_http.get("/agents").status_code == 403
        assert partner_http.get("/agents").status_code == 403

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


class TestContractAndReviewMatrix:
    def test_contract_role_matrix(self, client_http, agent_http, partner_http, admin_client, partner_profile_id, agent_user_id):
        now = datetime.now(timezone.utc).isoformat()

        c_client = client_http.post(
            "/contracts/client",
            json={"currency": "USD", "totalAmount": 100, "paymentType": "full"},
        )
        assert c_client.status_code == 201

        c_agent = agent_http.post(
            "/contracts/agent",
            json={"agentID": agent_user_id, "referenceID": f"A-{_uid()}", "fileurl": "https://x/a.pdf", "signedAt": now},
        )
        assert c_agent.status_code == 201

        c_partner = partner_http.post(
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
