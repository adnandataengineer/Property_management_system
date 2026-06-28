# finance/views.py
import os
import urllib.parse
import requests
from requests.auth import HTTPBasicAuth

from django.conf import settings
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.contrib.admin.views.decorators import staff_member_required


# ── Config ──────────────────────────────────────────────────────────────────
# Client credentials and the token-refresh logic live in one place: xero_client.
from .xero_client import (
    XERO_CLIENT_ID,
    XERO_CLIENT_SECRET,
    TOKEN_URL,
    get_valid_db_token,
    headers_for,
)

# Include offline_access if you want refresh tokens; remove if you truly don't need it
XERO_SCOPES = os.getenv(
    "XERO_SCOPES",
    "openid profile email accounting.transactions accounting.contacts offline_access"
)

AUTH_URL  = "https://login.xero.com/identity/connect/authorize"
CONNECTIONS_URL = "https://api.xero.com/connections"

# ── Helpers ─────────────────────────────────────────────────────────────────
def _redirect_uri(request) -> str:
    """
    EXACT redirect URI to send to Xero. Must match what's in the Xero dev portal.
    In production, set XERO_REDIRECT_URI in your environment.

    In local dev, Xero expects http://localhost (not 127.0.0.1/0.0.0.0).
    """
    # Use environment variable for production, fallback to localhost for development
    return os.getenv("XERO_REDIRECT_URI", "http://localhost:8000/finance/xero/callback")

def _get_tenant_id(access_token: str) -> str:
    """Return first tenantId from /connections."""
    r = requests.get(
        CONNECTIONS_URL,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json() or []
    if not data:
        raise RuntimeError("No Xero connections are available for this user/org.")
    return data[0]["tenantId"]

def _auth_headers(request) -> dict:
    """
    Headers required by the Accounting API (token + xero-tenant-id).

    Prefers the stored DB token, auto-refreshing it when expired, so the
    dashboard keeps working beyond the 30-minute access-token lifetime. Falls
    back to the raw session token only if no DB token exists.
    """
    token = get_valid_db_token()
    if token:
        return headers_for(token)

    tokens = request.session.get("xero_tokens") or {}
    tenant_id = request.session.get("xero_tenant_id") or ""
    return {
        "Authorization": f"Bearer {tokens.get('access_token', '')}",
        "xero-tenant-id": tenant_id,   # Xero requires this header for Accounting APIs
        "Accept": "application/json",
    }

# ── UI ──────────────────────────────────────────────────────────────────────
@staff_member_required
def dashboard(request):
    """Admin-only dashboard for Xero integration."""
    transactions = None
    sample = None
    tokens = request.session.get("xero_tokens")
    tenant_id = request.session.get("xero_tenant_id")
    
    # Date filtering
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if tokens and tokens.get("access_token") and tenant_id:
        # Fetch Bank Transactions
        headers = _auth_headers(request)
        
        # Build Xero API URL with filtering
        url = "https://api.xero.com/api.xro/2.0/BankTransactions"
        params = {}
        
        # Xero uses 'where' parameter for filtering
        # Example: Date >= DateTime(2023, 01, 01) AND Date <= DateTime(2023, 12, 31)
        where_clauses = []
        if start_date:
            y, m, d = start_date.split('-')
            where_clauses.append(f"Date >= DateTime({y}, {m}, {d})")
        if end_date:
            y, m, d = end_date.split('-')
            where_clauses.append(f"Date <= DateTime({y}, {m}, {d})")
            
        if where_clauses:
            params["where"] = " AND ".join(where_clauses)

        try:
            r = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=20,
            )
            if r.ok:
                data = r.json()
                transactions = data.get("BankTransactions") or []
            else:
                print(f"Error fetching transactions: {r.status_code} {r.text}")
        except Exception as e:
            print(f"Exception fetching transactions: {e}")

        except Exception as e:
            print(f"Exception fetching transactions: {e}")

    # Get Finance Settings
    from .models import FinanceSettings
    settings_obj = FinanceSettings.get_settings()
    
    xero_connected = bool(tokens and tokens.get("access_token") and tenant_id)

    context = {
        "title": "Finance Dashboard",
        "xero_connected": xero_connected,
        "transactions": transactions,
        "start_date": start_date,
        "end_date": end_date,
        "settings": settings_obj,
        "tenant_id": tenant_id, # Keep tenant_id for display if needed
        "site_title": "Smart Home Admin",
        "site_header": "Smart Home Administration",
    }
    return render(request, "finance/admin_dashboard.html", context)


# ── OAuth ───────────────────────────────────────────────────────────────────
@staff_member_required
def xero_start(request):
    """Kick off OAuth with Xero."""
    computed_uri = _redirect_uri(request)
    params = {
        "response_type": "code",
        "client_id": XERO_CLIENT_ID,
        "redirect_uri": computed_uri,
        "scope": XERO_SCOPES,
        "state": "xyz123",  # you can put a CSRF token or context here
    }
    url = AUTH_URL + "?" + urllib.parse.urlencode(params)
    # Handy when debugging exact redirect & scopes:
    print(f"\n[Xero Debug] Generated Redirect URI: {computed_uri}")
    print(f"[Xero Debug] Full Authorize URL: {url}\n")
    return redirect(url)

@staff_member_required
def xero_callback(request):
    """Receive ?code= from Xero and exchange it for tokens, then store tenant id."""
    if (err := request.GET.get("error")):
        return HttpResponseBadRequest(f"Xero returned error: {err}")

    code = request.GET.get("code")
    if not code:
        return HttpResponseBadRequest("Missing 'code' in callback URL.")

    resp = requests.post(
        TOKEN_URL,
        auth=HTTPBasicAuth(XERO_CLIENT_ID, XERO_CLIENT_SECRET),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _redirect_uri(request),  # must match start step
        },
        headers={"Accept": "application/json"},
        timeout=30,
    )
    if not resp.ok:
        return HttpResponseBadRequest(
            f"Token exchange failed: {resp.status_code}\n{resp.text}"
        )

    tokens = resp.json()
    request.session["xero_tokens"] = tokens

    # Fetch the tenant id you'll need for Accounting API
    try:
        tenant_id = _get_tenant_id(tokens["access_token"])
    except Exception as e:
        return HttpResponseBadRequest(f"Could not fetch tenant: {e}")
    request.session["xero_tenant_id"] = tenant_id

    # Save to DB for background/offline access
    from .models import XeroToken
    from django.utils import timezone
    import datetime
    
    # Calculate expiry
    expires_in = tokens.get("expires_in", 1800)
    expires_at = timezone.now() + datetime.timedelta(seconds=expires_in)
    
    # We only keep one active token set for simplicity (single org)
    XeroToken.objects.all().delete()
    XeroToken.objects.create(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        tenant_id=tenant_id,
        expires_at=expires_at
    )

    return redirect("finance:dashboard")

@staff_member_required
def xero_disconnect(request):
    """Clear session to reconnect/switch org."""
    request.session.pop("xero_tokens", None)
    request.session.pop("xero_tenant_id", None)
    
    # Clear DB tokens
    from .models import XeroToken
    XeroToken.objects.all().delete()
    
    return redirect("finance:dashboard")

@staff_member_required
def update_settings(request):
    if request.method == "POST":
        from .models import FinanceSettings
        settings_obj = FinanceSettings.get_settings()
        
        settings_obj.enable_monthly_invoices = request.POST.get("enable_monthly_invoices") == "on"
        settings_obj.enable_auto_reconciliation = request.POST.get("enable_auto_reconciliation") == "on"
        settings_obj.save()
        
        messages.success(request, "Settings updated successfully.")
    return redirect("finance:dashboard")

@staff_member_required
def run_reconciliation(request):
    if request.method == "POST":
        from django.core.management import call_command
        try:
            # We can call the management command directly
            # Note: This might take time, ideally should be async task (Celery)
            # For now, we run it synchronously but capture output?
            # Or just fire and forget if we trust it.
            # Let's run it and catch errors.
            call_command('reconcile_xero')
            messages.success(request, "Reconciliation process completed.")
        except Exception as e:
            messages.error(request, f"Error running reconciliation: {e}")
            
    return redirect("finance:dashboard")

# ── Sample API tests ────────────────────────────────────────────────────────
@require_GET
@staff_member_required
def test_contacts(request):
    if not request.session.get("xero_tokens"):
        return HttpResponseBadRequest("No token. Click Connect first.")
    r = requests.get(
        "https://api.xero.com/api.xro/2.0/Contacts",
        headers=_auth_headers(request),
        timeout=30,
    )
    if not r.ok:
        return HttpResponseBadRequest(f"Contacts failed: {r.status_code}\n{r.text}")
    data = r.json()
    return JsonResponse({"sample_contacts": (data.get("Contacts") or [])[:3]})

@require_GET
@staff_member_required
def test_bank_transactions(request):

    """Use this if you have bank transactions but no invoices."""
    if not request.session.get("xero_tokens"):
        return HttpResponseBadRequest("No token. Click Connect first.")
    r = requests.get(
        "https://api.xero.com/api.xro/2.0/BankTransactions",
        headers=_auth_headers(request),
        timeout=30,
    )
    if not r.ok:
        return HttpResponseBadRequest(
            f"BankTransactions failed: {r.status_code}\n{r.text}"
        )
    data = r.json()
    return JsonResponse({
        "count": len(data.get("BankTransactions", [])),
        "sample": (data.get("BankTransactions") or [])[:3],
    })
