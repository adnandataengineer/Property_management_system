from django.contrib import admin
from .models import Tenant, AgreementContent

@admin.register(AgreementContent)
class AgreementContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'content', 'rules')

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'property',        # not property_address
        'email',
        'smoker',          # not is_smoker
        'current_income',  # not current_in
        'license_fee',
        'deposit',
        'timestamp',
    )
    list_filter = (
        'smoker',
        'current_income',
    )
    search_fields = (
        'full_name',
        'email',
        'property__street_name',
    )
