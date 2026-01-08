from django.contrib import admin
from django.utils.html import format_html
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

    readonly_fields = ('display_signature',)

    fields = (
        'property',
        'notice_date',
        'move_in_date',
        'move_out_date',
        'full_name',
        'email',
        'phone_number',
        'pps_number',
        'passport_upload',
        'smoker',
        'consent_personal_data',
        'consent_share_data',
        'current_income',
        'license_fee',
        'deposit',
        'emergency_contact_name',
        'emergency_contact_phone',
        'display_signature',
        'booking_request',
        'payment_method',
    )

    def display_signature(self, obj):
        if obj.signature:
            return format_html(
                '<div style="display: inline-block; background-color: white; padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin-bottom: 5px;">'
                '<img src="{}" style="max-width: 520px; height: auto; display: block;" />'
                '</div>'
                '<br>'
                '<a href="{}" download="signature_{}.png" style="background: #007bff; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 12px; margin-right: 10px;">Download PNG</a>'
                '<span style="color: #666; font-size: 12px;">'
                'Status: {} characters. (Real signatures are usually >10,000)'
                '</span>',
                obj.signature,
                obj.signature,
                obj.pk,
                len(obj.signature)
            )
        return "No signature"
    display_signature.short_description = "Tenant Signature"
