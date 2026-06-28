from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from .models import FinanceDashboard, FinanceSettings


@admin.register(FinanceSettings)
class FinanceSettingsAdmin(admin.ModelAdmin):
    """Singleton settings: bank/payment routing details and invoice timing."""

    fieldsets = (
        ("Automation", {
            "fields": ("enable_monthly_invoices", "enable_auto_reconciliation", "reminder_lead_days"),
        }),
        ("Bank / Payment routing details", {
            "description": "Shown on the rent invoice PDF and in the email sent to tenants 10 days before payment.",
            "fields": (
                "bank_account_name", "bank_name", "bank_iban", "bank_bic",
                "bank_account_number", "bank_sort_code", "payment_reference_note",
            ),
        }),
    )

    def has_add_permission(self, request):
        # Only ever one settings row.
        return not FinanceSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FinanceDashboard)
class FinanceDashboardAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Redirect to the actual dashboard view
        return redirect("finance:dashboard")
