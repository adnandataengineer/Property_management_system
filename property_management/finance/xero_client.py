"""
Centralized Xero token handling.

Xero access tokens expire after 30 minutes. This module is the single place that
knows how to keep a valid token: it reads the stored XeroToken, refreshes it via
the rotating refresh token when it has (or is about to) expire, persists the new
tokens, and hands back ready-to-use auth headers.

Every Xero API caller (the dashboard, invoice generation, the reconcile command,
the monthly cron) should obtain headers through `get_db_auth_headers()` /
`get_valid_db_token()` so they never use a stale token.
"""
import os
import datetime

import requests
from requests.auth import HTTPBasicAuth

from django.utils import timezone


# ── Credentials (environment only — never commit these) ──────────────────────
# Set XERO_CLIENT_ID and XERO_CLIENT_SECRET in your env / DigitalOcean.
XERO_CLIENT_ID = os.getenv("XERO_CLIENT_ID", "")
XERO_CLIENT_SECRET = os.getenv("XERO_CLIENT_SECRET", "")

TOKEN_URL = "https://identity.xero.com/connect/token"

# Refresh a little early so a token never expires mid-request.
EXPIRY_BUFFER_SECONDS = 120


def _is_expired(token):
    """True if the token is missing an expiry or expires within the buffer window."""
    if not token.expires_at:
        return True
    return token.expires_at <= timezone.now() + datetime.timedelta(seconds=EXPIRY_BUFFER_SECONDS)


def refresh_access_token(token):
    """
    Exchange the stored refresh token for a fresh access token.

    Xero rotates refresh tokens, so the new refresh token MUST be saved. Returns
    the updated XeroToken on success, or None on failure.
    """
    if not token or not token.refresh_token:
        print("Xero refresh: no refresh token available.")
        return None

    try:
        resp = requests.post(
            TOKEN_URL,
            auth=HTTPBasicAuth(XERO_CLIENT_ID, XERO_CLIENT_SECRET),
            data={
                "grant_type": "refresh_token",
                "refresh_token": token.refresh_token,
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
    except Exception as e:
        print(f"Xero refresh: request error: {e}")
        return None

    if not resp.ok:
        # 400 here usually means the refresh token was revoked or already used
        # (it expires after 60 days of inactivity) — admin must reconnect.
        print(f"Xero refresh failed: {resp.status_code} {resp.text}")
        return None

    data = resp.json()
    token.access_token = data["access_token"]
    # A new refresh token is issued on every refresh; persist it or the next
    # refresh will fail.
    if data.get("refresh_token"):
        token.refresh_token = data["refresh_token"]
    expires_in = data.get("expires_in", 1800)
    token.expires_at = timezone.now() + datetime.timedelta(seconds=expires_in)
    token.save()
    print("Xero token refreshed successfully.")
    return token


def get_valid_db_token():
    """
    Return a non-expired XeroToken, refreshing it if necessary.

    Returns None if there is no stored token or the refresh failed (caller should
    treat this as 'not connected to Xero').
    """
    from .models import XeroToken

    token = XeroToken.objects.first()
    if not token:
        return None

    if _is_expired(token):
        token = refresh_access_token(token)

    return token


def headers_for(token):
    """Build the Accounting API headers for a given token."""
    return {
        "Authorization": f"Bearer {token.access_token}",
        "Xero-tenant-id": token.tenant_id,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def get_db_auth_headers():
    """
    Convenience: a valid headers dict from the stored token, or None if not
    connected / unable to refresh.
    """
    token = get_valid_db_token()
    if not token:
        return None
    return headers_for(token)
