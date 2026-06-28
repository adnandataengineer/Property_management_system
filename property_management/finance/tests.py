from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from properties.models import Property, Room, BookingRequest
from finance.models import FinanceSettings, XeroToken
from finance.invoice_email import (
    build_invoice_context,
    build_email_body,
    send_invoice_email,
)
from finance import xero_client
from properties.management.commands.send_rent_reminders import next_due_date


def make_booking(start_date, rent="500.00", bills="100.00", email="tenant@example.com",
                 status=BookingRequest.Status.APPROVED):
    prop = Property.objects.create(street_number="12", street_name="Main Street")
    room = Room.objects.create(
        property=prop,
        room_name="Room 1",
        rent=Decimal(rent),
        bill_price=Decimal(bills),
    )
    return BookingRequest.objects.create(
        room=room,
        full_name="Jane Doe",
        email=email,
        start_date=start_date,
        end_date=start_date + timedelta(days=365),
        status=status,
    )


def configured_settings():
    s = FinanceSettings.get_settings()
    s.reminder_lead_days = 10
    s.bank_account_name = "Grand HSH Services Ltd"
    s.bank_name = "Bank of Ireland"
    s.bank_iban = "IE29AIBK93115212345678"
    s.bank_bic = "AIBKIE2D"
    s.payment_reference_note = "Use your name and room as reference."
    s.save()
    return s


class NextDueDateTests(TestCase):
    def test_due_date_this_month_not_yet_passed(self):
        # Check-in on the 20th; today is the 5th -> due this month on the 20th.
        check_in = date(2026, 1, 20)
        today = date(2026, 6, 5)
        self.assertEqual(next_due_date(check_in, today), date(2026, 6, 20))

    def test_due_date_rolls_to_next_month_when_passed(self):
        # Today is after this month's due day -> next month.
        check_in = date(2026, 1, 10)
        today = date(2026, 6, 15)
        self.assertEqual(next_due_date(check_in, today), date(2026, 7, 10))

    def test_booking_not_started_yet(self):
        check_in = date(2026, 8, 1)
        today = date(2026, 6, 1)
        self.assertEqual(next_due_date(check_in, today), check_in)

    def test_end_of_month_clamps(self):
        # Check-in on the 31st; February has 28 days in 2026.
        check_in = date(2026, 1, 31)
        today = date(2026, 2, 1)
        self.assertEqual(next_due_date(check_in, today), date(2026, 2, 28))


class InvoiceContentTests(TestCase):
    def test_context_and_body_contain_charges_and_bank_details(self):
        booking = make_booking(date(2026, 1, 15))
        settings_obj = configured_settings()
        due = date(2026, 7, 15)

        ctx = build_invoice_context(booking, due, settings_obj)
        self.assertEqual(ctx["total"], "600.00")
        self.assertEqual(len(ctx["line_items"]), 2)
        self.assertEqual(ctx["payment_reference"], "Jane Doe - Room 1")

        body = build_email_body(ctx)
        self.assertIn("€600.00", body)            # euro currency, not $
        self.assertNotIn("$", body)
        self.assertIn("IE29AIBK93115212345678", body)  # IBAN present
        self.assertIn("Grand HSH Services Ltd", body)
        self.assertIn("July 15, 2026", body)      # due date

    def test_zero_bills_single_line_item(self):
        booking = make_booking(date(2026, 1, 15), bills="0.00")
        settings_obj = configured_settings()
        ctx = build_invoice_context(booking, date(2026, 7, 15), settings_obj)
        self.assertEqual(len(ctx["line_items"]), 1)
        self.assertEqual(ctx["total"], "500.00")


class SendInvoiceEmailTests(TestCase):
    @patch("finance.invoice_email.generate_invoice_pdf", return_value=b"%PDF-fake")
    def test_email_sent_with_pdf_attachment(self, mock_pdf):
        booking = make_booking(date(2026, 1, 15))
        settings_obj = configured_settings()
        sent, _ = send_invoice_email(booking, date(2026, 7, 15), settings_obj)

        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["tenant@example.com"])
        self.assertEqual(len(msg.attachments), 1)
        filename, content, mimetype = msg.attachments[0]
        self.assertTrue(filename.endswith(".pdf"))
        self.assertEqual(mimetype, "application/pdf")

    @patch("finance.invoice_email.generate_invoice_pdf", return_value=None)
    def test_email_still_sent_if_pdf_fails(self, mock_pdf):
        booking = make_booking(date(2026, 1, 15))
        settings_obj = configured_settings()
        sent, _ = send_invoice_email(booking, date(2026, 7, 15), settings_obj)
        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].attachments), 0)


class CommandTimingTests(TestCase):
    @patch("finance.invoice_email.generate_invoice_pdf", return_value=b"%PDF-fake")
    def test_sends_only_to_booking_due_in_lead_days(self, mock_pdf):
        configured_settings()  # lead_days = 10
        today = timezone.now().date()

        # Due in exactly 10 days -> should receive an invoice.
        due_booking = make_booking(today + timedelta(days=10), email="due@example.com")
        # Due in 5 days -> should NOT.
        make_booking(today + timedelta(days=5), email="early@example.com")

        call_command("send_rent_reminders")

        recipients = [addr for m in mail.outbox for addr in m.to]
        self.assertIn("due@example.com", recipients)
        self.assertNotIn("early@example.com", recipients)

    @patch("finance.invoice_email.generate_invoice_pdf", return_value=b"%PDF-fake")
    def test_pending_bookings_are_ignored(self, mock_pdf):
        configured_settings()
        today = timezone.now().date()
        make_booking(today + timedelta(days=10), email="pending@example.com",
                     status=BookingRequest.Status.PENDING)

        call_command("send_rent_reminders")
        self.assertEqual(len(mail.outbox), 0)


def _fake_token_response(access="new-access", refresh="new-refresh", expires_in=1800):
    resp = MagicMock()
    resp.ok = True
    resp.json.return_value = {
        "access_token": access,
        "refresh_token": refresh,
        "expires_in": expires_in,
    }
    return resp


class XeroTokenRefreshTests(TestCase):
    def _make_token(self, expires_delta_seconds):
        return XeroToken.objects.create(
            access_token="old-access",
            refresh_token="old-refresh",
            tenant_id="tenant-123",
            expires_at=timezone.now() + timedelta(seconds=expires_delta_seconds),
        )

    @patch("finance.xero_client.requests.post")
    def test_expired_token_is_refreshed_and_rotated(self, mock_post):
        # Token already expired.
        self._make_token(expires_delta_seconds=-60)
        mock_post.return_value = _fake_token_response()

        token = xero_client.get_valid_db_token()

        self.assertTrue(mock_post.called)
        self.assertEqual(token.access_token, "new-access")
        # Rotated refresh token must be persisted.
        self.assertEqual(token.refresh_token, "new-refresh")
        self.assertEqual(XeroToken.objects.get(pk=token.pk).refresh_token, "new-refresh")
        self.assertGreater(token.expires_at, timezone.now())

    @patch("finance.xero_client.requests.post")
    def test_valid_token_is_not_refreshed(self, mock_post):
        # Token valid for another 20 minutes -> no network call.
        self._make_token(expires_delta_seconds=1200)

        headers = xero_client.get_db_auth_headers()

        self.assertFalse(mock_post.called)
        self.assertEqual(headers["Authorization"], "Bearer old-access")
        self.assertEqual(headers["Xero-tenant-id"], "tenant-123")

    @patch("finance.xero_client.requests.post")
    def test_token_within_buffer_is_refreshed(self, mock_post):
        # Expires in 30s, inside the 120s buffer -> should refresh.
        self._make_token(expires_delta_seconds=30)
        mock_post.return_value = _fake_token_response(access="buf-access")

        headers = xero_client.get_db_auth_headers()

        self.assertTrue(mock_post.called)
        self.assertEqual(headers["Authorization"], "Bearer buf-access")

    @patch("finance.xero_client.requests.post")
    def test_failed_refresh_returns_none(self, mock_post):
        self._make_token(expires_delta_seconds=-60)
        bad = MagicMock()
        bad.ok = False
        bad.status_code = 400
        bad.text = "invalid_grant"
        mock_post.return_value = bad

        self.assertIsNone(xero_client.get_valid_db_token())
        self.assertIsNone(xero_client.get_db_auth_headers())

    def test_no_token_returns_none(self):
        self.assertIsNone(xero_client.get_valid_db_token())
        self.assertIsNone(xero_client.get_db_auth_headers())
