"""
Single entry point for the daily finance automation, intended to be run once a
day by the DigitalOcean App Platform scheduled (cron) job.

It runs, in order:
  1. send_rent_reminders        — emails the invoice + bank details 10 days
                                  before each tenant's rent due date.
  2. generate_monthly_invoices  — creates the Xero invoice on the due day.

Each sub-command is isolated so a failure in one does not stop the other.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the daily finance jobs (rent invoice emails + Xero invoice generation)."

    def handle(self, *args, **options):
        self.stdout.write("=== Daily finance tasks starting ===")

        for command_name in ("send_rent_reminders", "generate_monthly_invoices"):
            self.stdout.write(f"\n--- Running {command_name} ---")
            try:
                call_command(command_name)
            except Exception as e:
                # Log and continue; one failing job must not block the other.
                self.stderr.write(self.style.ERROR(f"{command_name} failed: {e}"))

        self.stdout.write(self.style.SUCCESS("\n=== Daily finance tasks complete ==="))
