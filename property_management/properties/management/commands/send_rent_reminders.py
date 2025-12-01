from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta, date
import calendar
from properties.models import BookingRequest


class Command(BaseCommand):
    help = 'Send rent reminders to tenants 7 days before monthly rent is due'

    def handle(self, *args, **options):
        today = timezone.now().date()
        reminder_date = today + timedelta(days=7)
        
        # Get all approved bookings
        approved_bookings = BookingRequest.objects.filter(
            status=BookingRequest.Status.APPROVED
        ).select_related('room', 'room__property')
        
        reminders_sent = 0
        
        for booking in approved_bookings:
            # Calculate the next rent due date based on check-in date
            # Rent is due monthly on the same day as check-in
            check_in = booking.start_date
            
            # Find the next rent due date after today
            months_since_checkin = (today.year - check_in.year) * 12 + (today.month - check_in.month)
            
            # Calculate next due date
            if months_since_checkin < 0:
                # Booking hasn't started yet, first rent due is check-in date
                next_due_date = check_in
            else:
                # Calculate the next month's due date
                next_month = check_in.month + months_since_checkin + 1
                next_year = check_in.year + (next_month - 1) // 12
                next_month = ((next_month - 1) % 12) + 1
                
                # Handle day of month (if check-in was on 31st and next month has 30 days, use 30th)
                last_day_of_next_month = calendar.monthrange(next_year, next_month)[1]
                day = min(check_in.day, last_day_of_next_month)
                
                next_due_date = date(next_year, next_month, day)
            
            # Check if we should send a reminder (7 days before due date)
            if next_due_date == reminder_date:
                room = booking.room
                property_address = f"{room.property.street_number} {room.property.street_name}"
                
                # Calculate total monthly payment
                total_rent = room.rent + room.bill_price
                
                subject = f"{settings.EMAIL_SUBJECT_PREFIX}Rent Reminder"
                message = f"""
Dear {booking.full_name},

This is a friendly reminder that your monthly rent payment is due on {next_due_date.strftime('%B %d, %Y')}.

Property: {property_address}
Room: {room.room_name}
Monthly Rent: ${room.rent}
Monthly Bills: ${room.bill_price}
Total Due: ${total_rent}

Please ensure payment is made on or before the due date.

If you have any questions, please contact us.

Best regards,
Property Management Team
                """.strip()
                
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [booking.email],
                        fail_silently=False,
                    )
                    reminders_sent += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Sent reminder to {booking.email} for {room} (due: {next_due_date})'
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to send to {booking.email}: {str(e)}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully sent {reminders_sent} rent reminder(s)')
        )
