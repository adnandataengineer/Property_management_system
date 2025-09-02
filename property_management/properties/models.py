from django.db import models
from django.conf import settings 
from django.utils import timezone 
from django.core.exceptions import ValidationError

class Property(models.Model):
    class UnitType(models.TextChoices):
        WHOLE_PROPERTY       = "WHOLE_PROPERTY",        "Whole property"
        WHOLE_APARTMENT      = "WHOLE_APARTMENT",       "Whole apartment"
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
        default=UnitType.WHOLE_PROPERTY,
        help_text="What the guest can book here.",
    )

    rent            = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    rent_margin     = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    actual_margin   = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    profit          = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    real_profit     = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    is_available = models.BooleanField(
        default=False,
        help_text="When True, the property is visible in the public list and open for booking requests."
    )

    def __str__(self):
        return f"{self.street_number} {self.street_name}"

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
    

class BookingRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    property = models.ForeignKey(
        'Property',
        on_delete=models.CASCADE,
        related_name='booking_requests'
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

    def clean(self):
        # Basic date validation
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after end date.")

    def __str__(self):
        return f"{self.full_name} → {self.property} ({self.status})"

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

