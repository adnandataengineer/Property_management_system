from django.contrib import admin
from .models import (
    Property,
    PropertyImage,          # keep your images
    BookingRequest,         # new
    AvailabilityAudit,      # new
)

from django.contrib import admin, messages
from django.conf import settings
from django.utils import timezone


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    inlines = [PropertyImageInline]
    list_display = ("id", "display_name", "is_available")
    list_filter = ("is_available",)
    search_fields = ("id",)  # safe: always exists

    @admin.display(description="Property")
    def display_name(self, obj):
        # Try common field names; fall back to __str__()
        for attr in ("title", "name", "property_name", "address"):
            if hasattr(obj, attr):
                val = getattr(obj, attr)
                if callable(val):
                    try:
                        val = val()
                    except TypeError:
                        pass
                if val:
                    return val
        return str(obj)

    def save_model(self, request, obj, form, change):
        # Log availability flips
        from_available = None
        if change:
            try:
                old = Property.objects.get(pk=obj.pk)
                from_available = old.is_available
            except Property.DoesNotExist:
                pass

        super().save_model(request, obj, form, change)

        if change and from_available is not None and from_available != obj.is_available:
            AvailabilityAudit.objects.create(
                property=obj,
                changed_by=getattr(request, "user", None),
                from_available=from_available,
                to_available=obj.is_available,
                changed_at=timezone.now(),
            )



@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id", "property", "full_name", "email",
        "start_date", "end_date", "status", "created_at"
    )
    list_filter = ("status", "created_at")
    search_fields = ("full_name", "email", "property__title")
    actions = ("approve_requests", "reject_requests")

    @admin.action(description="Approve selected requests")
    def approve_requests(self, request, queryset):
        updated = 0
        set_unavailable = getattr(settings, "BOOKING_SETS_UNAVAILABLE_ON_APPROVAL", True)

        for br in queryset.select_related("property"):
            if br.status != BookingRequest.Status.APPROVED:
                br.status = BookingRequest.Status.APPROVED
                br.save(update_fields=["status", "updated_at"])
                updated += 1

                if set_unavailable and br.property.is_available:
                    prop = br.property
                    prev = prop.is_available
                    prop.is_available = False
                    prop.save(update_fields=["is_available"])
                    AvailabilityAudit.objects.create(
                        property=prop,
                        changed_by=getattr(request, "user", None),
                        from_available=prev,
                        to_available=False,
                        changed_at=timezone.now(),
                    )

        self.message_user(request, f"Approved {updated} booking request(s).", level=messages.SUCCESS)

    @admin.action(description="Reject selected requests")
    def reject_requests(self, request, queryset):
        updated = queryset.exclude(status=BookingRequest.Status.REJECTED).update(
            status=BookingRequest.Status.REJECTED, updated_at=timezone.now()
        )
        self.message_user(request, f"Rejected {updated} booking request(s).", level=messages.WARNING)


@admin.register(AvailabilityAudit)
class AvailabilityAuditAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "from_available", "to_available", "changed_by", "changed_at")
    list_filter = ("from_available", "to_available", "changed_at")
    search_fields = ("property__title", "changed_by__username")
    readonly_fields = ("property", "from_available", "to_available", "changed_by", "changed_at")

    def has_add_permission(self, request):
        return False
