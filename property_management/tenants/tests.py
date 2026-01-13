from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from django.conf import settings
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from properties.models import Property, Room, BookingRequest
from tenants.models import AgreementContent, Tenant

class TenantOnboardingTests(TestCase):
    def setUp(self):
        # Create Property
        self.property = Property.objects.create(
            street_number="123",
            street_name="Test St"
        )
        
        # Create Room
        self.room = Room.objects.create(
            property=self.property,
            room_name="Room 101",
            room_type="PRIVATE_SINGLE",
            rent=1000.00
        )
        
        # Create BookingRequest
        self.booking = BookingRequest.objects.create(
            room=self.room,
            full_name="Test Tenant",
            email="tenant@example.com",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365),
            status=BookingRequest.Status.APPROVED
        )
        
        # Create AgreementContent
        self.agreement = AgreementContent.objects.create(
            title="Test Agreement",
            content="This is a test agreement content.",
            rules="No loud music.",
            is_active=True
        )
        
        self.client = Client()
        self.url = reverse('tenants:onboarding', args=[self.booking.pk])
        
        # Form data
        self.form_data = {
            'full_name': 'Test Tenant',
            'email': 'tenant@example.com',
            'phone_number': '1234567890',
            'pps_number': '1234567A',
            'move_in_date': self.booking.start_date, # Should be ignored/read-only but needed for form validation
            'move_out_date': self.booking.end_date,
            'current_income': 5000,
            'smoker': False,
            'emergency_contact': 'Mom 999999',
            'property_address': str(self.property),
            'consent_personal_data': True,
            'rules_regulations': True,
            'signature_data': "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            # File upload needs to be handled separately in the post
        }

    @patch('xhtml2pdf.pisa.pisaDocument')
    def test_successful_onboarding_sends_emails(self, mock_pisa):
        """Test that successful PDF generation sends emails to both Tenant and Admin"""
        # Mock successful PDF generation
        def pisa_side_effect(src, dest, encoding='UTF-8'):
            dest.write(b"dummy pdf content")
            mock_pdf = MagicMock()
            mock_pdf.err = 0
            return mock_pdf
            
        mock_pisa.side_effect = pisa_side_effect
        
        # Create a mock file for upload
        from django.core.files.uploadedfile import SimpleUploadedFile
        passport_file = SimpleUploadedFile("passport.pdf", b"file_content", content_type="application/pdf")
        
        data = self.form_data.copy()
        data['passport_upload'] = passport_file
        
        response = self.client.post(self.url, data, follow=True)
        
        # Check standard success
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tenants/success.html')
        
        # CHECK EMAILS
        # We expect 2 emails:
        # 1. To Admin (New Signed Agreement)
        # 2. To Tenant (Your Signed Agreement)
        self.assertEqual(len(mail.outbox), 2)
        
        # Verify emails
        subjects = [e.subject for e in mail.outbox]
        self.assertIn(f"New Signed Agreement - {self.booking.full_name}", subjects)
        self.assertIn(f"Your Signed Agreement - {settings.COMPANY_NAME}", subjects)
        
        # Verify attachments
        # Both emails should have attachments
        self.assertEqual(len(mail.outbox[0].attachments), 1)
        self.assertEqual(len(mail.outbox[1].attachments), 1)
        
        # Verify Tenant record created
        tenant = Tenant.objects.get(email='tenant@example.com')
        self.assertTrue(tenant.agreement_pdf)

    @patch('xhtml2pdf.pisa.pisaDocument')
    def test_pdf_generation_failure_sends_admin_warning(self, mock_pisa):
        """Test that failed PDF generation sends email ONLY to Admin with warning"""
        # Mock FAILED PDF generation
        mock_pdf = MagicMock()
        mock_pdf.err = 1 # Error!
        mock_pisa.return_value = mock_pdf
        
        # Create a mock file for upload
        from django.core.files.uploadedfile import SimpleUploadedFile
        passport_file = SimpleUploadedFile("passport.pdf", b"file_content", content_type="application/pdf")
        
        data = self.form_data.copy()
        data['passport_upload'] = passport_file
        
        response = self.client.post(self.url, data, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tenants/success.html')
        
        # CHECK EMAILS
        # We expect ONLY 1 email:
        # 1. To Admin (New Signed Agreement)
        # Tenant should NOT receive email
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertIn("New Signed Agreement", email.subject)
        self.assertIn("homesweethome.pmanagement@gmail.com", email.to)
        
        # Check body for failure message
        self.assertIn("PDF generation failed", email.body)
        
        # Verify NO attachment
        self.assertEqual(len(email.attachments), 0)
