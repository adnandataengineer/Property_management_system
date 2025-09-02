from datetime import date, timedelta
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, RegexValidator

from .models import BookingRequest

PHONE_RE = r"^\+?[0-9()\-.\s]{7,20}$"   # +353 86 123 4567, (01) 234-5678, etc.

class BookingRequestForm(forms.ModelForm):
    # Honeypot to stop bots
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    full_name = forms.CharField(
        max_length=120,
        validators=[MinLengthValidator(2)],
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Your full name"}),
        label="Full name",
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "you@example.com"}),
        label="Email",
    )
    phone = forms.CharField(
        required=False,
        validators=[RegexValidator(PHONE_RE, "Enter a valid phone number.")],
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional"}),
        label="Phone (optional)",
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="Check-in date",
    )
    notes = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-control", "placeholder": "Anything we should know?"}),
        label="Additional notes (optional)",
    )

    class Meta:
        model = BookingRequest
        fields = ["full_name", "email", "phone", "start_date", "notes"]  # end_date intentionally not exposed

    def __init__(self, *args, **kwargs):
        # the view passes Property so we can run duplicate checks
        self.property = kwargs.pop("property", None)
        super().__init__(*args, **kwargs)

    def clean_full_name(self):
        name = self.cleaned_data["full_name"].strip()
        name = " ".join(name.split())  # collapse multiple spaces
        import re
        if not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$", name):
            raise ValidationError("Use letters, spaces, apostrophes, or hyphens only.")
        return name

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_start_date(self):
        sd = self.cleaned_data["start_date"]
        today = date.today()
        if sd < today:
            raise ValidationError("Check-in date cannot be in the past.")
        if sd > today + timedelta(days=540):  # ~18 months
            raise ValidationError("Pick a date within the next 18 months.")
        return sd

    def clean_notes(self):
        notes = (self.cleaned_data.get("notes") or "").strip()
        import re
        if re.search(r"https?://|www\.", notes):
            raise ValidationError("Please don’t include links.")
        return notes

    def clean(self):
        cleaned = super().clean()

        # Honeypot must be empty
        if cleaned.get("website"):
            raise ValidationError("Form flagged as spam.")

        # Prevent duplicate pending requests in last 24h for same property+email
        prop = self.property
        email = cleaned.get("email")
        if prop and email:
            from django.utils import timezone
            recent = timezone.now() - timedelta(hours=24)
            exists = BookingRequest.objects.filter(
                property=prop,
                email__iexact=email,
                status=BookingRequest.Status.PENDING,
                created_at__gte=recent,
            ).exists()
            if exists:
                raise ValidationError("You’ve already submitted a request recently. We’ll be in touch soon.")
        return cleaned
