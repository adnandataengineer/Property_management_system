from django.core.management.base import BaseCommand
from django.conf import settings
from finance.models import XeroToken
from finance.utils import (
    _auth_headers, 
    get_xero_bank_accounts, 
    get_unreconciled_statement_lines, 
    find_matching_invoice, 
    create_xero_payment
)
import requests

class Command(BaseCommand):
    help = 'Automates Xero reconciliation by matching bank statement lines to invoices.'

    def handle(self, *args, **options):
        self.stdout.write("Starting Xero Reconciliation...")

        from finance.models import FinanceSettings
        settings = FinanceSettings.get_settings()
        # Allow force run via argument if we wanted, but for now strict check
        if not settings.enable_auto_reconciliation:
             # We might want to allow manual run from dashboard even if disabled?
             # The dashboard calls this command. 
             # If we want the button to work even if "Auto" is disabled, we should pass an argument.
             # But user asked to enable/disable it. 
             # Let's assume the setting controls the *automated* run (cron).
             # But since we don't distinguish caller, let's just check the setting.
             # OR we add an argument --force.
             if 'force' not in options or not options['force']:
                 self.stdout.write(self.style.WARNING("Auto reconciliation is DISABLED in settings."))
                 # We will allow it if called with --force, but we haven't added that arg yet.
                 # Let's just return for now to be safe.
                 return

        # 1. Get Tokens
        token = XeroToken.objects.first()
        if not token:
            self.stdout.write(self.style.ERROR("No Xero token found. Please connect Xero in the dashboard."))
            return

        # Mock request object for _auth_headers or construct manually
        # Since _auth_headers expects a request with session, we'll manually construct headers here
        # or update utils to handle no-request. 
        # For now, let's construct manually using the token we fetched.
        headers = {
            "Authorization": f"Bearer {token.access_token}",
            "Xero-tenant-id": token.tenant_id,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # 2. Get Bank Accounts
        accounts = get_xero_bank_accounts(headers)
        if not accounts:
            self.stdout.write(self.style.WARNING("No bank accounts found."))
            return

        for account in accounts:
            account_name = account.get("Name")
            account_id = account.get("AccountID")
            self.stdout.write(f"Checking account: {account_name} ({account_id})")

            # 3. Get Statement Lines
            lines = get_unreconciled_statement_lines(headers, account_id)
            self.stdout.write(f"  Found {len(lines)} statement lines.")

            for line in lines:
                amount = line.get("Amount")
                date = line.get("TransactionDate") # YYYY-MM-DD
                reference = line.get("Reference")
                
                # Only process money coming in (Credit)
                if amount and float(amount) > 0:
                    self.stdout.write(f"  Processing line: {date} - {amount} - {reference}")
                    
                    # 4. Find Matching Invoice
                    invoice = find_matching_invoice(headers, amount, reference)
                    
                    if invoice:
                        invoice_num = invoice.get("InvoiceNumber")
                        invoice_id = invoice.get("InvoiceID")
                        self.stdout.write(self.style.SUCCESS(f"    MATCH FOUND: Invoice {invoice_num}"))
                        
                        # 5. Create Payment
                        if create_xero_payment(headers, invoice_id, account_id, amount, date):
                            self.stdout.write(self.style.SUCCESS("    Payment created successfully."))
                        else:
                            self.stdout.write(self.style.ERROR("    Failed to create payment."))
                    else:
                        self.stdout.write("    No matching authorised invoice found.")
                
        self.stdout.write(self.style.SUCCESS("Reconciliation process completed."))
