from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import TenantOnboardingForm
from properties.models import BookingRequest

def tenant_onboarding(request, booking_id=None):
    """
    Public view for tenants to provide their details.
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
        }
        if booking.room and booking.room.property:
             initial_data['property_address'] = str(booking.room.property)

    if request.method == 'POST':
        form = TenantOnboardingForm(request.POST, request.FILES, booking_id=booking_id, initial=initial_data)
        if form.is_valid():
            tenant = form.save(commit=False)
            if booking:
                tenant.booking_request = booking
                if booking.room:
                    tenant.property = booking.room.property
                    # Auto-fill deposit from rent
                    tenant.deposit = booking.room.rent
                    tenant.license_fee = booking.room.rent
                # Copy the admin-set move-out date from the booking
                if booking.end_date:
                    tenant.move_out_date = booking.end_date

            # Update BookingRequest status
            if booking:
                from django.utils import timezone
                booking.signed_at = timezone.now()
                booking.save()

            tenant.save()

            # --- Generate PDF Agreement ---
            pdf_generated = False
            pdf_bytes = None
            
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
                    pdf_bytes = result.getvalue()  # Store PDF bytes for email attachment
                    tenant.agreement_pdf.save(f"Agreement_{tenant.full_name}_{tenant.pk}.pdf", ContentFile(pdf_bytes))
                    tenant.save()
                    pdf_generated = True
                    print(f"PDF generated successfully for tenant {tenant.pk}")
                else:
                    print(f"PDF generation had errors for tenant {tenant.pk}")
                    
            except Exception as e:
                print(f"Error generating PDF for tenant {tenant.pk}: {e}")
                import traceback
                traceback.print_exc()

            # --- Send Emails: Only send to tenant if PDF generated successfully ---
            try:
                from django.core.mail import EmailMessage
                from django.conf import settings
                
                # ALWAYS send email to Admin (for tracking, even if PDF fails)
                admin_email = EmailMessage(
                    subject=f"New Signed Agreement - {tenant.full_name}",
                    body=f"A new agreement has been signed by {tenant.full_name}.\n\n" +
                         f"Email: {tenant.email}\n" +
                         f"Property: {tenant.property}\n" +
                         (f"PDF attached.\n" if pdf_generated else f"PDF generation failed - check logs.\n"),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=["homesweethome.pmanagement@gmail.com"],
                )
                
                # Attach PDF for admin if generated
                if pdf_generated and pdf_bytes:
                    admin_email.attach(f"Agreement_{tenant.full_name}.pdf", pdf_bytes, 'application/pdf')
                
                # Attach passport to admin email if uploaded
                if tenant.passport_upload:
                    try:
                        passport_file = tenant.passport_upload
                        passport_file.open('rb')
                        passport_bytes = passport_file.read()
                        passport_file.close()
                        passport_name = passport_file.name.split('/')[-1]
                        admin_email.attach(passport_name, passport_bytes, 'application/octet-stream')
                        print(f"Passport attached to admin email for tenant {tenant.pk}")
                    except Exception as pe:
                        print(f"Could not attach passport for tenant {tenant.pk}: {pe}")
                    
                admin_email.send()
                print(f"Admin email sent successfully")

                # ONLY send email to Tenant if PDF was generated successfully
                if pdf_generated and pdf_bytes:
                    tenant_email = EmailMessage(
                        subject=f"Your Signed Agreement - {settings.COMPANY_NAME}",
                        body=f"Dear {tenant.full_name},\n\nThank you for completing your licensee agreement.\n\n" + 
                             f"Please find attached your signed agreement.\n\n" +
                             f"Best regards,\n{settings.COMPANY_NAME}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[tenant.email],
                    )
                    
                    tenant_email.attach(f"Agreement_{tenant.full_name}.pdf", pdf_bytes, 'application/pdf')
                    tenant_email.send()
                    print(f"Tenant email sent successfully to {tenant.email} with PDF attachment")
                else:
                    print(f"Skipping tenant email - PDF generation failed for tenant {tenant.pk}")

            except Exception as e:
                print(f"Error sending emails for tenant {tenant.pk}: {e}")
                import traceback
                traceback.print_exc()
                # Don't block success page if email fails, but log it clearly

            
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
        form = TenantOnboardingForm(initial=initial_data, booking_id=booking_id)

    return render(request, 'tenants/onboarding_form.html', {
        'form': form,
        'agreement': agreement
    })