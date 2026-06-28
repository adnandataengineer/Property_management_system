from django.db import models

class FinanceDashboard(models.Model):
    class Meta:
        managed = False  # No database table creation
        verbose_name = "Finance Dashboard"
        verbose_name_plural = "Finance Dashboard"

class XeroToken(models.Model):
    access_token = models.TextField()
    refresh_token = models.TextField()
    tenant_id = models.CharField(max_length=100, blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Xero Token (updated {self.updated_at})"

class FinanceSettings(models.Model):
    enable_monthly_invoices = models.BooleanField(default=False, help_text="Automatically generate monthly invoices")
    enable_auto_reconciliation = models.BooleanField(default=False, help_text="Automatically reconcile bank transactions")

    # How many days before the rent due date the invoice + payment instructions
    # are emailed to the tenant. Client requirement: 10 days before.
    reminder_lead_days = models.PositiveIntegerField(
        default=10,
        help_text="Days before the rent due date to email the invoice and payment details.",
    )

    # Bank / payment routing details shown on the invoice and in the email.
    # Editable in the Django admin so they never need to be hard-coded.
    bank_account_name = models.CharField(max_length=200, blank=True, default="", help_text="Account holder / beneficiary name")
    bank_name = models.CharField(max_length=200, blank=True, default="", help_text="Name of the bank")
    bank_iban = models.CharField(max_length=64, blank=True, default="", help_text="IBAN")
    bank_bic = models.CharField(max_length=32, blank=True, default="", help_text="BIC / SWIFT code")
    bank_account_number = models.CharField(max_length=64, blank=True, default="", help_text="Account number (optional)")
    bank_sort_code = models.CharField(max_length=32, blank=True, default="", help_text="Sort code (optional)")
    payment_reference_note = models.CharField(
        max_length=255,
        blank=True,
        default="Please use your full name and room as the payment reference.",
        help_text="Instruction shown to the tenant for the transfer reference.",
    )

    def has_bank_details(self):
        """True once the essential routing details have been filled in."""
        return bool(self.bank_account_name and self.bank_iban)

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and FinanceSettings.objects.exists():
            return FinanceSettings.objects.first()
        super().save(*args, **kwargs)

    def __str__(self):
        return "Finance Settings"

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
