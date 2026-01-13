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
                if booking.room:
                    tenant.property = booking.room.property
                    # Auto-fill deposit from rent
                    tenant.deposit = booking.room.rent
                    tenant.license_fee = booking.room.rent # Assuming license fee is also rent?

            # Update BookingRequest status
            if booking:
                from django.utils import timezone
                booking.signed_at = timezone.now()
                booking.save()

            tenant.save()

            # --- Generate PDF Agreement ---
            try:
                from django.conf import settings
                from django.template.loader import get_template
                from xhtml2pdf import pisa
                from django.core.files.base import ContentFile
                from io import BytesIO

                template_path = 'tenants/pdf/agreement_pdf.html'
                context = {
                    'tenant': tenant,
                    'company_name': settings.COMPANY_NAME,
                    'agreement': agreement,
                }
                template = get_template(template_path)
                html = template.render(context)
                result = BytesIO()
                # Explicitly specify UTF-8 encoding for proper character rendering
                pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, encoding='UTF-8')
                if not pdf.err:
                    tenant.agreement_pdf.save(f"Agreement_{tenant.full_name}_{tenant.pk}.pdf", ContentFile(result.getvalue()))
                    tenant.save()
                    
                    # --- Send Email with Attachment ---
                    from django.core.mail import EmailMessage
                    
                    # Email to Tenant
                    tenant_email = EmailMessage(
                        subject=f"Your Signed Agreement - {settings.COMPANY_NAME}",
                        body=f"Dear {tenant.full_name},\n\nPlease find attached your signed licensee agreement.\n\nBest regards,\n{settings.COMPANY_NAME}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[tenant.email],
                    )
                    tenant_email.attach(tenant.agreement_pdf.name, tenant.agreement_pdf.read(), 'application/pdf')
                    tenant_email.send()
                    
                    # Email to Admin
                    admin_email = EmailMessage(
                        subject=f"New Signed Agreement - {tenant.full_name}",
                        body=f"A new agreement has been signed by {tenant.full_name}.\n\nSee attached PDF.",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=["homesweethome.pmanagement@gmail.com"], # Hardcoded as per request "admin"
                    )
                    # Reset pointer for re-reading if not using storage open/close logic carefully, 
                    # but FileField.read() usually handles it or we use result.getvalue()
                    tenant.agreement_pdf.seek(0)
                    admin_email.attach(tenant.agreement_pdf.name, tenant.agreement_pdf.read(), 'application/pdf')
                    admin_email.send()

            except Exception as e:
                print(f"Error generating PDF or sending email: {e}")
                # Don't block success page if email fails, but log it.

            
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