from django.core.management.base import BaseCommand
from django.utils import timezone
from tenants.models import Tenant
from finance.utils import create_invoice_for_tenant
from finance.models import XeroToken
from django.db import models
import datetime

class Command(BaseCommand):
    help = 'Generates monthly invoices for active tenants based on their move-in date.'

    def handle(self, *args, **options):
        self.stdout.write("Starting Monthly Invoice Generation...")
        
        from finance.models import FinanceSettings
        settings = FinanceSettings.get_settings()
        if not settings.enable_monthly_invoices:
            self.stdout.write(self.style.WARNING("Monthly invoice generation is DISABLED in settings. Exiting."))
            return
        
        today = timezone.now().date()
        
        if not XeroToken.objects.exists():
             self.stdout.write(self.style.ERROR("No Xero token found. Cannot generate invoices."))
             return

        # Find active tenants
        active_tenants = Tenant.objects.filter(
            move_in_date__isnull=False
        ).filter(
             models.Q(move_out_date__isnull=True) | models.Q(move_out_date__gt=today)
        )

        for tenant in active_tenants:
            invoice_day = tenant.move_in_date.day
            
            # Simple check: is today the invoice day?
            # TODO: Handle end of month edge cases (e.g. 31st)
            if today.day == invoice_day:
                self.stdout.write(f"Generating invoice for {tenant.full_name} (Day {invoice_day})")
                
                if create_invoice_for_tenant(tenant, today):
                    self.stdout.write(self.style.SUCCESS(f"  Invoice generated for {tenant.full_name}"))
                else:
                    self.stdout.write(self.style.ERROR(f"  Failed to generate invoice for {tenant.full_name}"))
            else:
                # Optional: verbose output
                # self.stdout.write(f"Skipping {tenant.full_name} (Due day {invoice_day}, Today {today.day})")
                pass

        self.stdout.write(self.style.SUCCESS("Monthly Invoice Generation Completed."))
