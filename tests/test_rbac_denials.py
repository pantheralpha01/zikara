"""
Negative RBAC matrix tests.

These tests assert forbidden role/action combinations stay forbidden.
"""

import uuid

import pytest


@pytest.fixture(scope="module")
def seeded_resources(admin_client, partner_http, client_http, client_user_id, agent_user_id, partner_profile_id):
    # catalog
    cat = admin_client.post("/categories", json={"name": "RBAC Neg Cat", "slug": f"rbac-neg-{uuid.uuid4().hex[:8]}"})
    assert cat.status_code == 201, cat.text
    cat_id = cat.json()["id"]

    svc = admin_client.post(
        "/services",
        json={"categoryId": cat_id, "name": "RBAC Neg Svc", "slug": f"rbac-neg-svc-{uuid.uuid4().hex[:8]}"},
    )
    assert svc.status_code == 201, svc.text

    listing = partner_http.post(
        "/listings",
        json={
            "partnerId": partner_profile_id,
            "categoryId": cat_id,
            "serviceId": svc.json()["id"],
            "title": "RBAC Neg Listing",
            "description": "seed",
            "city": "Nairobi",
            "country": "Kenya",
            "priceFrom": 120,
            "pricingType": "per_person",
            "currency": "USD",
        },
    )
    assert listing.status_code == 201, listing.text

    booking = client_http.post(
        "/bookings",
        json={
            "clientId": client_user_id,
            "agentId": agent_user_id,
            "currency": "USD",
            "totalAmount": 220,
            "paymentType": "full",
            "costAtBooking": 220,
            "status": "confirmed",
        },
    )
    assert booking.status_code == 201, booking.text

    return {
        "listing_id": listing.json()["id"],
        "booking_id": booking.json()["id"],
        "partner_profile_id": partner_profile_id,
        "agent_user_id": agent_user_id,
    }


def test_client_cannot_create_quote(client_http, partner_profile_id, agent_user_id):
    r = client_http.post(
        "/quotes",
        json={
            "currency": "USD",
            "totalAmount": 100,
            "paymentType": "full",
            "agentId": agent_user_id,
            "partners": [{"partnerId": partner_profile_id, "PartnerAmount": 100}],
        },
    )
    assert r.status_code == 403


def test_partner_cannot_create_booking(partner_http, client_user_id, agent_user_id):
    r = partner_http.post(
        "/bookings",
        json={
            "clientId": client_user_id,
            "agentId": agent_user_id,
            "currency": "USD",
            "totalAmount": 100,
            "paymentType": "full",
            "costAtBooking": 100,
            "status": "confirmed",
        },
    )
    assert r.status_code == 403


def test_client_cannot_complete_booking(client_http, seeded_resources):
    r = client_http.post(f"/bookings/{seeded_resources['booking_id']}/complete")
    assert r.status_code == 403


def test_partner_cannot_complete_booking(partner_http, seeded_resources):
    r = partner_http.post(f"/bookings/{seeded_resources['booking_id']}/complete")
    assert r.status_code == 403


def test_client_cannot_access_partner_wallet(client_http, seeded_resources):
    r = client_http.get(f"/wallets/{seeded_resources['partner_profile_id']}")
    assert r.status_code == 403


def test_agent_cannot_access_partner_wallet(agent_http, seeded_resources):
    r = agent_http.get(f"/wallets/{seeded_resources['partner_profile_id']}")
    assert r.status_code == 403


def test_partner_cannot_access_foreign_wallet(partner_http):
    r = partner_http.get(f"/wallets/{uuid.uuid4()}")
    assert r.status_code == 403


def test_non_admin_cannot_manage_agents_clients(client_http, agent_http, partner_http):
    # Clients and partners cannot list agents or clients
    for c in (client_http, partner_http):
        assert c.get("/agents").status_code == 403
        assert c.get("/clients").status_code == 403
    # Agents cannot list agents (admin/manager only) but CAN list clients (per spec)
    assert agent_http.get("/agents").status_code == 403


def test_non_admin_cannot_approve_listing(agent_http, partner_http, client_http, seeded_resources):
    for c in (agent_http, partner_http, client_http):
        r = c.post(f"/listings/{seeded_resources['listing_id']}/approve")
        assert r.status_code == 403


def test_partner_cannot_initiate_payment(partner_http, seeded_resources):
    r = partner_http.post(
        "/payments/initiate",
        json={
            "bookingId": seeded_resources["booking_id"],
            "amount": 10,
            "currency": "USD",
            "provider": "stripe",
        },
    )
    assert r.status_code == 403
