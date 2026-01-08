import requests
from django.conf import settings
from .views import _auth_headers

def create_invoice_from_booking(booking_request, request):
    """
    Creates an invoice in Xero for the given BookingRequest.
    Returns True if successful, False otherwise.
    """
    # Try to get headers from session, or fallback to DB
    try:
        headers = _auth_headers(request)
    except Exception:
        # If session fails (e.g. anonymous user), try DB
        from .models import XeroToken
        token = XeroToken.objects.first()
        if not token:
            print("No Xero token found in DB.")
            return False
            
        # TODO: Check expiry and refresh if needed
        # For now assuming token is valid or we just fail
        headers = {
            "Authorization": f"Bearer {token.access_token}",
            "Xero-tenant-id": token.tenant_id,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    
    # 1. Ensure contact exists or create one
    contact_data = {
        "Name": booking_request.full_name,
        "EmailAddress": booking_request.email,
        "Phones": [{"PhoneType": "DEFAULT", "PhoneNumber": booking_request.phone}] if booking_request.phone else []
    }
    
    # Try to find contact by email first to avoid duplicates
    # (Simplified: just create/update based on Name)
    
    # 2. Create Invoice
    # Line items: Rent + Bills
    line_items = []
    
    # Rent
    if booking_request.room.rent > 0:
        line_items.append({
            "Description": f"Rent for {booking_request.room.room_name} ({booking_request.start_date.strftime('%B %Y')})",
            "Quantity": 1.0,
            "UnitAmount": float(booking_request.room.rent),
            "AccountCode": "200", # Sales/Revenue - adjust as needed
        })
        
    # Bills
    if booking_request.room.bill_price > 0:
        line_items.append({
            "Description": "Utilities/Bills",
            "Quantity": 1.0,
            "UnitAmount": float(booking_request.room.bill_price),
            "AccountCode": "200",
        })
        
    invoice_data = {
        "Type": "ACCREC", # Accounts Receivable
        "Contact": contact_data,
        "Date": str(booking_request.start_date),
        "DueDate": str(booking_request.start_date), # Due on check-in
        "LineItems": line_items,
        "Status": "DRAFT", # Create as draft so admin can review
        "Reference": f"Booking #{booking_request.pk}"
    }
    
    try:
        r = requests.post(
            "https://api.xero.com/api.xro/2.0/Invoices",
            headers=headers,
            json={"Invoices": [invoice_data]},
            timeout=30
        )
        
        if r.ok:
            print(f"Invoice created successfully: {r.json()}")
            return True
        else:
            print(f"Failed to create invoice: {r.status_code} {r.text}")
            return False
            
    except Exception as e:
        print(f"Exception creating invoice: {e}")
        return False

def get_xero_bank_accounts(headers):
    """Fetch all bank accounts from Xero."""
    try:
        r = requests.get(
            "https://api.xero.com/api.xro/2.0/Accounts",
            headers=headers,
            params={"where": 'Type=="BANK"'},
            timeout=30
        )
        if r.ok:
            return r.json().get("Accounts", [])
        print(f"Failed to fetch accounts: {r.text}")
        return []
    except Exception as e:
        print(f"Error fetching accounts: {e}")
        return []

def get_unreconciled_statement_lines(headers, bank_account_id):
    """
    Fetch recent bank statements and extract unreconciled lines.
    """
    try:
        # Fetch last 5 statements
        r = requests.get(
            "https://api.xero.com/api.xro/2.0/BankStatements",
            headers=headers,
            params={"where": f'BankAccount.AccountID==GUID("{bank_account_id}")', "order": "Date DESC", "page": 1},
            timeout=30
        )
        if not r.ok:
            print(f"Failed to fetch statements: {r.text}")
            return []
            
        statements = r.json().get("BankStatements", [])
        lines = []
        for stmt in statements:
            lines.extend(stmt.get("StatementLines", []))
        return lines
    except Exception as e:
        print(f"Error fetching statement lines: {e}")
        return []

def find_matching_invoice(headers, amount, reference=None):
    """
    Find an AUTHORISED invoice with the exact amount.
    Optionally match reference if provided.
    """
    where_clause = f'Status=="AUTHORISED" AND AmountDue=={amount}'
    if reference:
        # Escape reference if needed, simple check here
        where_clause += f' AND Reference=="{reference}"'
        
    try:
        r = requests.get(
            "https://api.xero.com/api.xro/2.0/Invoices",
            headers=headers,
            params={"where": where_clause},
            timeout=30
        )
        if r.ok:
            invoices = r.json().get("Invoices", [])
            if invoices:
                return invoices[0] # Return first match
        return None
    except Exception as e:
        print(f"Error finding invoice: {e}")
        return None

def create_xero_payment(headers, invoice_id, account_id, amount, date):
    """Create a payment in Xero to reconcile the invoice."""
    payment_data = {
        "Invoice": {"InvoiceID": invoice_id},
        "Account": {"AccountID": account_id},
        "Amount": amount,
        "Date": date,
        "Status": "AUTHORISED"
    }
    
    try:
        r = requests.post(
            "https://api.xero.com/api.xro/2.0/Payments",
            headers=headers,
            json={"Payments": [payment_data]},
            timeout=30
        )
        if r.ok:
            print(f"Payment created: {r.json()}")
            return True
        else:
            print(f"Failed to create payment: {r.text}")
            return False
    except Exception as e:
        print(f"Error creating payment: {e}")
        return False

def create_invoice_for_tenant(tenant, invoice_date=None):
    """
    Creates a recurring invoice for a Tenant.
    Uses tenant.booking_request to get room/rent details.
    """
    if not invoice_date:
        from django.utils import timezone
        invoice_date = timezone.now().date()
        
    # Get headers (reuse logic or call _auth_headers if we had request, but we don't here)
    # So we copy the DB token logic
    from .models import XeroToken
    token = XeroToken.objects.first()
    if not token:
        print("No Xero token found.")
        return False
        
    headers = {
        "Authorization": f"Bearer {token.access_token}",
        "Xero-tenant-id": token.tenant_id,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    
    booking = tenant.booking_request
    if not booking or not booking.room:
        print(f"Tenant {tenant} has no booking/room details.")
        return False
        
    # Line items
    line_items = []
    
    # Rent
    if booking.room.rent > 0:
        line_items.append({
            "Description": f"Rent for {booking.room.room_name} ({invoice_date.strftime('%B %Y')})",
            "Quantity": 1.0,
            "UnitAmount": float(booking.room.rent),
            "AccountCode": "200",
        })
        
    # Bills
    if booking.room.bill_price > 0:
        line_items.append({
            "Description": "Utilities/Bills",
            "Quantity": 1.0,
            "UnitAmount": float(booking.room.bill_price),
            "AccountCode": "200",
        })
        
    contact_data = {
        "Name": tenant.full_name,
        "EmailAddress": tenant.email,
    }
    
    # Determine status based on payment method
    # If Cash, set to DRAFT so admin can manually approve when cash is received
    # If Bank Transfer (default), set to AUTHORISED
    xero_status = "AUTHORISED"
    if hasattr(tenant, 'payment_method') and tenant.payment_method == 'cash':
        xero_status = "DRAFT"

    invoice_data = {
        "Type": "ACCREC",
        "Contact": contact_data,
        "Date": str(invoice_date),
        "DueDate": str(invoice_date),
        "LineItems": line_items,
        "Status": xero_status,
        "Reference": f"Rent {invoice_date.strftime('%b %Y')}"
    }
    
    try:
        r = requests.post(
            "https://api.xero.com/api.xro/2.0/Invoices",
            headers=headers,
            json={"Invoices": [invoice_data]},
            timeout=30
        )
        if r.ok:
            print(f"Recurring Invoice created: {r.json()}")
            return True
        else:
            print(f"Failed to create recurring invoice: {r.text}")
            return False
    except Exception as e:
        print(f"Error creating recurring invoice: {e}")
        return False
