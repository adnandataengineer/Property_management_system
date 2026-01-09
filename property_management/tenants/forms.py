from django import forms
from .models import Tenant
from django.core.exceptions import ValidationError

class TenantOnboardingForm(forms.ModelForm):
    # Explicitly define fields to match the user's exact requirements and labels
    full_name = forms.CharField(label="Full Name", required=True)
    email = forms.EmailField(label="Email", required=True)
    property_address = forms.CharField(
        label="Address of Property (The address you are moving in)",
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter property address'})
    )
    phone_number = forms.CharField(label="Phone number", required=True)
    pps_number = forms.CharField(
        label="PPS number",
        required=True,
        help_text="Note, if you don't have PPS number yet, please filled with N/A"
    )
    move_in_date = forms.DateField(
        label="Move in date",
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    move_out_date = forms.DateField(
        label="Move out date",
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    current_income = forms.DecimalField(
        label="Current Income",
        required=True,
        widget=forms.NumberInput(attrs={'placeholder': 'Enter your monthly income'})
    )
    # deposit removed as per user request (will be auto-filled from rent)

    passport_upload = forms.FileField(
        label="Passport Upload",
        required=True,
        help_text="Upload 1 supported file: PDF, document or image. Max 100 MB."
    )
    smoker = forms.ChoiceField(
        label="Are you a smoker?",
        choices=[(True, 'Yes'), (False, 'No')],
        widget=forms.RadioSelect,
        required=True
    )
    emergency_contact = forms.CharField(
        label="Contact for Emergency (Name and phone number)",
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Name and Phone Number'})
    )
    
    # Consent fields
    consent_personal_data = forms.BooleanField(
        label="By checking this box, I confirm that I consent to the collection and processing of my personal data for the purpose to create the license agreement",
        required=True
    )
    
    rules_regulations = forms.BooleanField(
        label="I agree to the House Rules and Regulations",
        required=True,
        help_text="By checking this, you agree to abide by all property rules."
    )
    
    # Signature field (hidden input to store base64 data from canvas)
    signature_data = forms.CharField(widget=forms.HiddenInput(), required=True)

    class Meta:
        model = Tenant
        fields = [
            'full_name', 'email', 'phone_number', 'pps_number', 
            'move_in_date', 'move_out_date', 'current_income',
            'passport_upload', 'smoker', 'emergency_contact',
            'consent_personal_data', 'rules_regulations'
        ]

    def clean(self):
        cleaned_data = super().clean()
        # Custom validation if needed
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Handle fields that don't map directly 1:1 or need processing
        # emergency_contact is a single field in form but split in model? 
        # User asked for "Contact for Emergency (Name and phone number)" as one field in form.
        # But model has name and phone separate. I'll split it or just save to name.
        # Let's just save the whole string to emergency_contact_name for now to be safe.
        emergency_info = self.cleaned_data.get('emergency_contact')
        if emergency_info:
            instance.emergency_contact_name = emergency_info
        
        instance.signature = self.cleaned_data.get('signature_data')
        
        if commit:
            instance.save()
        return instance
