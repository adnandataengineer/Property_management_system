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
