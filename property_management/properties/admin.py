from django.contrib import admin
from .models import (
    Property,
    PropertyImage,
    Room,
    RoomImage,
    CommonArea,
    BookingRequest,
    AvailabilityAudit,
)

from django.contrib import admin, messages
from django.conf import settings
from django.utils import timezone




class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


class RoomInline(admin.TabularInline):
    model = Room
    extra = 1
    fields = ('room_name', 'room_type', 'rent', 'bill_price', 'is_available', 'has_twin_beds', 'image', 'description')
    list_display = ('room_name', 'room_type', 'rent', 'bill_price', 'is_available')


class CommonAreaInline(admin.TabularInline):
    model = CommonArea
    extra = 1
    fields = ('name', 'description')


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    inlines = [PropertyImageInline, RoomInline, CommonAreaInline]
    list_display = ("id", "display_name", "available_rooms_count")
    list_filter = ("is_available",)
    search_fields = ("id",)

    @admin.display(description="Available Rooms")
    def available_rooms_count(self, obj):
        """Show count of available rooms"""
        return obj.property_rooms.filter(is_available=True).count()


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
        "start_date", "end_date", "status", "agreement_sent", "onboarding_link"
    )
    list_filter = ("status", "created_at", "agreement_sent")
    search_fields = ("full_name", "email", "property__street_name")
    actions = ("approve_requests", "reject_requests", "generate_invoices")

    readonly_fields = ("onboarding_link", "created_at", "updated_at")

    @admin.display(description="Tenant Onboarding Link")
    def onboarding_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        
        if not obj.pk:
            return "-"
            
        url = reverse("tenants:onboarding", args=[obj.pk])
        # In production, use request.build_absolute_uri but here we don't have request easily in list_display unless we use a different approach.
        # But for readonly field in detail view, we can just show the path or try to construct full URL if possible.
        # Let's just show the path for now, or use a hardcoded domain if needed. 
        # Actually, for admin, relative path is clickable.
        return format_html('<a href="{}" target="_blank">Open Onboarding Form</a> (Share this link)', url)

    def save_model(self, request, obj, form, change):
        if change:
            # Check if status changed to APPROVED
            old = BookingRequest.objects.get(pk=obj.pk)
            if old.status != BookingRequest.Status.APPROVED and obj.status == BookingRequest.Status.APPROVED:
                self._send_agreement_email(request, obj)
        elif obj.status == BookingRequest.Status.APPROVED:
            # New object created as APPROVED
            self._send_agreement_email(request, obj)
            
        super().save_model(request, obj, form, change)

    def _send_agreement_email(self, request, br, check_already_sent=True):
        from django.core.mail import send_mail
        from django.urls import reverse
        
        # Check if email was already sent (in database, not the form value)
        if check_already_sent:
            try:
                old_br = BookingRequest.objects.get(pk=br.pk)
                if old_br.agreement_sent:
                    print(f"Email already sent for booking {br.pk}, skipping.")
                    return
            except BookingRequest.DoesNotExist:
                # New object, proceed
                pass

        br.agreement_sent = True
        # We don't save here because save_model will save, or the caller will save. 
        # But for bulk actions we might need to save.
        # Let's just set the flag. The caller should save.
        # Actually save_model saves AFTER this. So modifying obj is fine.
        
        # Use the new Tenant Onboarding Form URL
        agreement_url = request.build_absolute_uri(
            reverse("tenants:onboarding", args=[br.pk])
        )
        
        subject = f"Booking Approved! Please complete your onboarding — {br.property}"
        message = (
            f"Hi {br.full_name},\n\n"
            "Good news! Your booking request has been approved.\n"
            "Please click the link below to provide your details, upload your passport, and sign the agreement:\n\n"
            f"{agreement_url}\n\n"
            "Once submitted, we will generate your invoice.\n\n"
            "Thanks,\nSmart Home Management"
        )
        print(f"Attempting to send email to {br.email}...")
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [br.email],
                fail_silently=False
            )
            print("Email sent successfully.")
        except Exception as e:
            print(f"Failed to send email: {e}")
            self.message_user(request, f"Failed to send email: {e}", level=messages.ERROR)
            return

        self.message_user(request, f"Onboarding email sent to {br.email}", level=messages.SUCCESS)

    @admin.action(description="Approve selected requests")
    def approve_requests(self, request, queryset):
        updated = 0
        set_unavailable = getattr(settings, "BOOKING_SETS_UNAVAILABLE_ON_APPROVAL", True)

        for br in queryset.select_related("room", "room__property"):
            if br.status != BookingRequest.Status.APPROVED:
                br.status = BookingRequest.Status.APPROVED
                self._send_agreement_email(request, br)
                br.save() # Save status and agreement_sent
                updated += 1

                if set_unavailable and br.room and br.room.is_available:
                    room = br.room
                    room.is_available = False
                    room.save(update_fields=["is_available"])

        self.message_user(request, f"Approved {updated} booking request(s).", level=messages.SUCCESS)

    @admin.action(description="Reject selected requests")
    def reject_requests(self, request, queryset):
        updated = queryset.exclude(status=BookingRequest.Status.REJECTED).update(
            status=BookingRequest.Status.REJECTED, updated_at=timezone.now()
        )
        self.message_user(request, f"Rejected {updated} booking request(s).", level=messages.WARNING)

    @admin.action(description="Generate invoices for signed bookings")
    def generate_invoices(self, request, queryset):
        from finance.utils import create_invoice_from_booking
        
        # Check if admin has Xero tokens
        if not request.session.get("xero_tokens"):
            self.message_user(
                request, 
                "You must connect to Xero first. Go to Finance Dashboard (/finance/) and click 'Connect to Xero'.",
                level=messages.ERROR
            )
            return
        
        success_count = 0
        failed_count = 0
        
        for br in queryset:
            # Only generate invoices for approved and signed bookings
            if br.status != BookingRequest.Status.APPROVED:
                self.message_user(request, f"Booking {br.pk} is not approved, skipping.", level=messages.WARNING)
                continue
            
            if not br.signed_at:
                self.message_user(request, f"Booking {br.pk} is not signed yet, skipping.", level=messages.WARNING)
                continue
            
            print(f"Generating invoice for booking {br.pk}...")
            if create_invoice_from_booking(br, request):
                success_count += 1
                self.message_user(request, f"Invoice created for booking {br.pk} ({br.full_name})", level=messages.SUCCESS)
            else:
                failed_count += 1
                self.message_user(request, f"Failed to create invoice for booking {br.pk}", level=messages.ERROR)
        
        if success_count > 0:
            self.message_user(request, f"Successfully created {success_count} invoice(s).", level=messages.SUCCESS)
        if failed_count > 0:
            self.message_user(request, f"Failed to create {failed_count} invoice(s).", level=messages.ERROR)




class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 1


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    inlines = [RoomImageInline]
    list_display = ("id", "property", "room_name", "room_type", "rent", "bill_price", "is_available", "has_twin_beds", "image")
    list_filter = ("is_available", "room_type", "has_twin_beds")
    search_fields = ("room_name", "property__street_name", "property__street_number")
    list_editable = ("is_available",)


@admin.register(CommonArea)
class CommonAreaAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "name")
    search_fields = ("name", "property__street_name")


@admin.register(AvailabilityAudit)
class AvailabilityAuditAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "from_available", "to_available", "changed_by", "changed_at")
    list_filter = ("from_available", "to_available", "changed_at")
    search_fields = ("property__title", "changed_by__username")
    readonly_fields = ("property", "from_available", "to_available", "changed_by", "changed_at")

    def has_add_permission(self, request):
        return False
