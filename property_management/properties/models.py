from django.db import models
from django.conf import settings 
from django.utils import timezone 
from django.core.exceptions import ValidationError

class Property(models.Model):
    class UnitType(models.TextChoices):
        # WHOLE_PROPERTY & WHOLE_APARTMENT removed as per request
        STUDIO               = "STUDIO",                "Studio"

        PRIVATE_SINGLE       = "PRIVATE_SINGLE",        "Private single room"
        PRIVATE_DOUBLE       = "PRIVATE_DOUBLE",        "Private double room"
        TWIN_ROOM            = "TWIN_ROOM",             "Twin room (2 singles)"
        TRIPLE_ROOM          = "TRIPLE_ROOM",           "Triple room"
        QUAD_ROOM            = "QUAD_ROOM",             "Quad room"

        ENSUITE_SINGLE       = "ENSUITE_SINGLE",        "Ensuite single room"
        ENSUITE_DOUBLE       = "ENSUITE_DOUBLE",        "Ensuite double room"
        ENSUITE_TWIN         = "ENSUITE_TWIN",          "Ensuite twin room"

        TWIN_2_BED_SINGLE    = "TWIN_2_BED_SINGLE",     "Single bed in twin bed room"
        DORM_4_BED_SINGLE    = "DORM_4_BED_SINGLE",     "Single bed in 4-bed dorm"
        DORM_6_BED_SINGLE    = "DORM_6_BED_SINGLE",     "Single bed in 6-bed dorm"
        DORM_8_BED_SINGLE    = "DORM_8_BED_SINGLE",     "Single bed in 8-bed dorm"

        DORM_FEMALE_ONLY     = "DORM_FEMALE_ONLY",      "Female-only dorm bed"
        DORM_MALE_ONLY       = "DORM_MALE_ONLY",        "Male-only dorm bed"


    street_number   = models.CharField(max_length=10, blank=True, null=True)
    street_name     = models.CharField(max_length=100, blank=True, null=True)
    complement      = models.CharField(max_length=100, blank=True, null=True)
    landlord        = models.CharField(max_length=100, blank=True, null=True)
    date_acquired   = models.DateField(blank=True, null=True)
    internet        = models.BooleanField(default=False)
    electricity     = models.BooleanField(default=False)
    gas             = models.BooleanField(default=False)
    trash           = models.BooleanField(default=False)
    prepay          = models.BooleanField(default=False)
    date_released   = models.DateField(blank=True, null=True)
    contract_length = models.IntegerField(help_text="Contract length in months", default=0)

    property_video  = models.FileField(
        blank=True,
        null=True,
        help_text="Optional video tour of the property"
    )


    maintenance     = models.TextField(blank=True)
    rooms           = models.IntegerField(default=0)
    bathrooms       = models.DecimalField(max_digits=3, decimal_places=1, default=0)

    # UPDATED: dropdown with your requested options
    type            = models.CharField(
        max_length=50,
        choices=UnitType.choices,
        default=UnitType.PRIVATE_SINGLE,
        help_text="What the guest can book here.",
    )

    is_available = models.BooleanField(
        default=False,
        help_text="When True, the property is visible in the public list and open for booking requests."
    )

    def __str__(self):
        return f"{self.street_number} {self.street_name}"

    def get_available_room_count(self):
        return self.property_rooms.filter(is_available=True).count()


class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image    = models.ImageField()
    caption  = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Image #{self.pk} for {self.property}"


class Room(models.Model):
    """Individual room within a property that can be rented separately"""
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='property_rooms',
        help_text="The property this room belongs to"
    )
    room_name = models.CharField(
        max_length=100,
        help_text="Name or identifier for the room (e.g., 'Room 1', 'Master Bedroom')"
    )
    room_type = models.CharField(
        max_length=50,
        choices=Property.UnitType.choices,
        default=Property.UnitType.PRIVATE_SINGLE,
        help_text="Type of room/accommodation"
    )
    image = models.ImageField(
        upload_to='room_images/',
        blank=True,
        null=True,
        help_text="Image of the specific room"
    )
    rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Monthly rent for this room"
    )
    bill_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Monthly bill price for this room"
    )
    is_available = models.BooleanField(
        default=True,
        help_text="When True, the room is visible publicly and available for booking"
    )
    has_twin_beds = models.BooleanField(
        default=False,
        help_text="True if this room has 2 single beds (twin room setup)"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description specific to this room"
    )

    class Meta:
        ordering = ['property', 'room_name']
        unique_together = ['property', 'room_name']

    def __str__(self):
        return f"{self.property} - {self.room_name}"


class RoomImage(models.Model):
    """Images specific to individual rooms"""
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField()
    caption = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Image #{self.pk} for {self.room}"


class CommonArea(models.Model):
    """Shared/common areas in a property (kitchen, living room, etc.)"""
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='common_areas',
        help_text="The property this common area belongs to"
    )
    name = models.CharField(
        max_length=100,
        help_text="Name of the common area (e.g., 'Kitchen', 'Living Room', 'Garden')"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the common area"
    )

    class Meta:
        ordering = ['property', 'name']
        verbose_name_plural = "Common areas"

    def __str__(self):
        return f"{self.property} - {self.name}"

    


class BookingRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    room = models.ForeignKey(
        'Room',
        on_delete=models.CASCADE,
        related_name='booking_requests',
        help_text="The specific room being requested for booking",
        null=True,
        blank=True
    )

    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    notes = models.TextField(blank=True, max_length=500)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def property(self):
        """Convenience property to access the property through the room"""
        return self.room.property if self.room else None

    def clean(self):
        # Basic date validation
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after end date.")

    def __str__(self):
        return f"{self.full_name} → {self.room} ({self.status})"

    class Meta:
        ordering = ['-created_at']



class AvailabilityAudit(models.Model):
    property = models.ForeignKey(
        'Property',
        on_delete=models.CASCADE,
        related_name='availability_audits'
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="User who made the availability change (if known)."
    )
    from_available = models.BooleanField()
    to_available = models.BooleanField()
    changed_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.property} availability {self.from_available} → {self.to_available} @ {self.changed_at:%Y-%m-%d %H:%M}"

