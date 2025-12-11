from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from .models import FinanceDashboard

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
