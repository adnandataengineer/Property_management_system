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

    def __str__(self):
        return self.full_name or f"Tenant #{self.pk}"
