"""
Outbound notifications from Zikara → Chakra HQ.

Chakra uses OAuth2 Bearer tokens. We send the stored access token; if Chakra
returns 401 we attempt a token refresh using the client credentials and retry once.

All calls are fire-and-forget (errors are logged, not raised) so a Chakra outage
never breaks Zikara's own booking/quote flows.
"""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _refresh_access_token() -> str | None:
    """Use the refresh token to obtain a new access token from Chakra."""
    if not settings.CHAKRA_BASE_URL or not settings.CHAKRA_REFRESH_TOKEN:
        return None
    try:
        resp = httpx.post(
            f"{settings.CHAKRA_BASE_URL}/oauth/token",
            json={
                "grant_type": "refresh_token",
                "refresh_token": settings.CHAKRA_REFRESH_TOKEN,
                "client_id": settings.CHAKRA_CLIENT_ID,
                "client_secret": settings.CHAKRA_CLIENT_SECRET,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception as exc:
        logger.warning("Chakra token refresh failed: %s", exc)
    return None


def _post(path: str, payload: dict) -> bool:
    """
    POST to Chakra. Returns True on success.
    Retries once with a refreshed token on 401.
    """
    if not settings.CHAKRA_BASE_URL or not settings.CHAKRA_ACCESS_TOKEN:
        return False

    url = f"{settings.CHAKRA_BASE_URL.rstrip('/')}{path}"

    try:
        resp = httpx.post(url, json=payload, headers=_headers(settings.CHAKRA_ACCESS_TOKEN), timeout=10)

        if resp.status_code == 401:
            # Token expired — refresh and retry once
            new_token = _refresh_access_token()
            if new_token:
                settings.CHAKRA_ACCESS_TOKEN = new_token  # update in-memory for this process
                resp = httpx.post(url, json=payload, headers=_headers(new_token), timeout=10)

        if resp.status_code < 300:
            return True

        logger.warning("Chakra notification failed [%s] %s: %s", resp.status_code, path, resp.text[:200])

    except Exception as exc:
        logger.warning("Chakra notification error [%s]: %s", path, exc)

    return False


# ---------------------------------------------------------------------------
# Public notification functions — call these from routers
# ---------------------------------------------------------------------------

def notify_enquiry_status(chakra_enquiry_id: str, status: str, extra: dict | None = None) -> None:
    """
    Tell Chakra the status of an enquiry changed.
    e.g. status = "quote_sent" | "booking_confirmed" | "booking_cancelled" | "booking_completed"
    """
    if not chakra_enquiry_id:
        return
    payload: dict[str, Any] = {"enquiry_id": chakra_enquiry_id, "status": status}
    if extra:
        payload.update(extra)
    _post("/webhooks/zikara/enquiry-status", payload)


def notify_agent_assigned(chakra_enquiry_id: str, agent_id: str, agent_name: str) -> None:
    """Tell Chakra which Zikara agent was auto-assigned to an enquiry."""
    if not chakra_enquiry_id:
        return
    _post("/webhooks/zikara/agent-assigned", {
        "enquiry_id": chakra_enquiry_id,
        "agent_id": str(agent_id),
        "agent_name": agent_name,
    })
