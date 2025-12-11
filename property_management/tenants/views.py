from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import TenantOnboardingForm
from properties.models import BookingRequest

def tenant_onboarding(request, booking_id=None):
    """
    Public view for tenants to provide their details.
    If booking_id is provided, we pre-fill some info and link the tenant.
    If booking_id is provided, we pre-fill some info and link the tenant.
    """
    from .models import AgreementContent
    agreement = AgreementContent.objects.filter(is_active=True).first()
    
    booking = None
    initial_data = {}
    
    if booking_id:
        booking = get_object_or_404(BookingRequest, pk=booking_id)
        # Pre-fill data from booking request
        initial_data = {
            'full_name': booking.full_name,
            'email': booking.email,
            'phone_number': booking.phone,
            'move_in_date': booking.start_date,
            # 'property_address': str(booking.room.property) if booking.room else '' 
            # Note: property_address is a text field in form, we can pre-fill it.
        }
        if booking.room and booking.room.property:
             initial_data['property_address'] = str(booking.room.property)

    if request.method == 'POST':
        form = TenantOnboardingForm(request.POST, request.FILES)
        if form.is_valid():
            tenant = form.save(commit=False)
            if booking:
                tenant.booking_request = booking
                # Also link property from booking if not already set (though form doesn't set property FK directly yet)
                if booking.room:
                    tenant.property = booking.room.property
            
            # If no booking/property linked, we might have an issue as Tenant.property is required.
            # For now, if no booking, we might fail or need a fallback. 
            # Assuming this flow ALWAYS starts from a booking link for now.
            
            # Update BookingRequest status
            if booking:
                from django.utils import timezone
                booking.signed_at = timezone.now()
                booking.save()

            tenant.save()
            
            # Trigger Xero Invoice Generation
            if booking:
                from finance.utils import create_invoice_from_booking
                # We pass request, but utils will fallback to DB if session is empty
                if create_invoice_from_booking(booking, request):
                    messages.success(request, "Invoice generated successfully.")
                else:
                    # Don't show error to user, just log it (already logged in utils)
                    pass
            
            messages.success(request, "Thank you! Your information has been submitted successfully.")
            return render(request, 'tenants/success.html')
    else:
        form = TenantOnboardingForm(initial=initial_data)

    return render(request, 'tenants/onboarding_form.html', {
        'form': form,
        'agreement': agreement
    })