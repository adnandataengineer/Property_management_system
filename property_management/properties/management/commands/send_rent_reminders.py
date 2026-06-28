from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
import calendar
from properties.models import BookingRequest
from finance.models import FinanceSettings
from finance.invoice_email import send_invoice_email


def next_due_date(check_in, today):
    """Return the next rent due date on/after today, based on the check-in day."""
    months_since_checkin = (today.year - check_in.year) * 12 + (today.month - check_in.month)

    if months_since_checkin < 0:
        # Booking hasn't started yet: first rent is due on the check-in date.
        return check_in

    next_month = check_in.month + months_since_checkin
    next_year = check_in.year + (next_month - 1) // 12
    next_month = ((next_month - 1) % 12) + 1
    last_day = calendar.monthrange(next_year, next_month)[1]
    candidate = date(next_year, next_month, min(check_in.day, last_day))

    # If this month's due date has already passed, roll to next month.
    if candidate < today:
        next_month = check_in.month + months_since_checkin + 1
        next_year = check_in.year + (next_month - 1) // 12
        next_month = ((next_month - 1) % 12) + 1
        last_day = calendar.monthrange(next_year, next_month)[1]
        candidate = date(next_year, next_month, min(check_in.day, last_day))

    return candidate


class Command(BaseCommand):
    help = "Email tenants their rent invoice + bank payment details N days before rent is due (default 10)."

    def handle(self, *args, **options):
        today = timezone.now().date()

        finance_settings = FinanceSettings.get_settings()
        lead_days = finance_settings.reminder_lead_days or 10
        target_due_date = today + timedelta(days=lead_days)

        if not finance_settings.has_bank_details():
            self.stdout.write(self.style.WARNING(
                "Bank/payment routing details are not configured in Finance Settings. "
                "Invoices will be sent without complete payment details."
            ))

        approved_bookings = BookingRequest.objects.filter(
            status=BookingRequest.Status.APPROVED
        ).select_related("room", "room__property")

        sent = 0
        for booking in approved_bookings:
            if not booking.start_date:
                continue

            due_date = next_due_date(booking.start_date, today)

            # Send when the due date is exactly `lead_days` away.
            if due_date != target_due_date:
                continue

            try:
                ok, detail = send_invoice_email(booking, due_date, finance_settings)
                if ok:
                    sent += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"Sent invoice to {booking.email} for {booking.room} "
                        f"(due {due_date}, {lead_days} days ahead) - {detail}"
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f"Skipped {booking}: {detail}"
                    ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Failed to send to {booking.email}: {e}"
                ))

        self.stdout.write(self.style.SUCCESS(
            f"Successfully sent {sent} invoice email(s) for rent due on {target_due_date}."
        ))
