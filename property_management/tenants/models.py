# tenants/models.py

from django.db import models
from properties.models import Property

class Tenant(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='tenants'
    )
    # Allow this to be NULL so existing rows don’t need a default
    notice_date     = models.DateField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    move_in_date    = models.DateField(blank=True, null=True)
    move_out_date   = models.DateField(blank=True, null=True)
    notice_date     = models.DateField(blank=True, null=True)
    full_name       = models.CharField(max_length=200, blank=True, null=True)
    email           = models.EmailField(blank=True, null=True)
    phone_number    = models.CharField(max_length=20, blank=True, null=True)
    pps_number      = models.CharField(max_length=50, blank=True, null=True)
    passport_upload = models.FileField(upload_to='tenant_passports/', blank=True, null=True)
    smoker          = models.BooleanField(default=False)
    consent_personal_data = models.BooleanField(
        default=False,
        help_text="I consent to the collection and processing of my personal data for the license agreement"
    )
    consent_share_data = models.BooleanField(
        default=False,
        help_text="I consent to the licensor sharing my data for the licensee agreement"
    )
    current_income  = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    license_fee     = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    deposit         = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    # New fields for onboarding workflow
    emergency_contact_name = models.CharField(max_length=200, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=50, blank=True, null=True)
    signature = models.TextField(blank=True, null=True, help_text="Base64 encoded signature image")
    
    PAYMENT_METHOD_CHOICES = [
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
    ]
    payment_method = models.CharField(
        max_length=10, 
        choices=PAYMENT_METHOD_CHOICES, 
        default='bank',
        help_text="If Cash is selected, invoices will be created as Draft in Xero for manual approval."
    )
    
    booking_request = models.ForeignKey(
        'properties.BookingRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tenants',
        help_text="Linked booking request"
    )

    def __str__(self):
        return self.full_name or f"Tenant #{self.pk}"

class AgreementContent(models.Model):
    title = models.CharField(max_length=200, default="Standard Agreement")
    content = models.TextField(help_text="Main agreement text")
    rules = models.TextField(help_text="House rules and regulations")
    is_active = models.BooleanField(default=False, help_text="Only one agreement should be active at a time")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.is_active:
            # Deactivate all others
            AgreementContent.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"
