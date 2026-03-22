import os
import django
from datetime import date, timedelta
import io

# Setup Django Environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "property_management.settings")
django.setup()

from properties.models import Property, Room, BookingRequest
from tenants.models import AgreementContent
from django.test import Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

def test_email_workflow():
    print("--- Starting Email Workflow Test ---")
    
    # 1. Create a Test Property
    Property.objects.filter(street_name="Test Email St").delete()
    prop = Property.objects.create(
        street_number="999",
        street_name="Test Email St",
        is_available=True,
        type=Property.UnitType.PRIVATE_SINGLE
    )
    print(f"[+] Created Property: {prop}")
    
    # 2. Create a Test Room
    room = Room.objects.create(
        property=prop,
        room_name="Test Email Room",
        room_type=Property.UnitType.PRIVATE_SINGLE,
        rent=1000,
        is_available=True
    )
    print(f"[+] Created Room: {room}")

    # 3. Create or get active AgreementContent
    agreement = AgreementContent.objects.filter(is_active=True).first()
    if not agreement:
        agreement = AgreementContent.objects.create(
            title="Test Email Agreement",
            content="This is a test agreement.",
            rules="No loud noises.",
            is_active=True
        )
        print("[+] Created active AgreementContent")
    else:
        print("[+] Found active AgreementContent")

    # 4. Create a BookingRequest
    start_dt = date.today()
    end_dt = date.today() + timedelta(days=30)
    
    booking = BookingRequest.objects.create(
        room=room,
        full_name="Tester McTestFace",
        email="muhammadadnan.py@gmail.com",
        phone="1234567890",
        start_date=start_dt,
        end_date=end_dt,
        status=BookingRequest.Status.APPROVED
    )
    print(f"[+] Created BookingRequest ID {booking.id} with status APPROVED")

    # 5. Simulate the Onboarding POST Request
    print("[+] Simulating Form Submission (This should trigger PDF gen and email sends)...")
    client = Client()
    
    url = reverse('tenants:onboarding', kwargs={'booking_id': booking.id})
    
    # Create a dummy image for signature and passport upload
    import base64
    valid_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
    dummy_passport = io.BytesIO(valid_png)
    passport_file = SimpleUploadedFile("passport.png", dummy_passport.read(), content_type="image/png")
    
    post_data = {
        'full_name': 'Tester McTestFace',
        'email': 'muhammadadnan.py@gmail.com',
        'phone_number': '1234567890',
        'move_in_date': start_dt.strftime('%Y-%m-%d'),
        'move_out_date': end_dt.strftime('%Y-%m-%d'),
        # Adding consent checkboxes that might be required
        'consent_personal_data': True,
        'rules_regulations': True,
        'emergency_contact': 'Emergency Contact 0987654321',
        # Required fields according to form
        'pps_number': 'PPS1234X',
        'smoker': False,
        'current_income': 50000,
        'payment_method': 'bank',
        'signature_data': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
        'passport_upload': passport_file
    }
    
    try:
        response = client.post(url, data=post_data, follow=True, HTTP_HOST='localhost')
        print(f"[+] Received response: Status {response.status_code}")
        if response.status_code == 200:
            if hasattr(response, 'context') and response.context is not None and 'form' in response.context and response.context['form'].errors:
                print(f"[-] Form Errors: {response.context['form'].errors}")
            else:
                print("[+] Form submission looks successful (or missing context).")
            # Verify if tenant was created
            from tenants.models import Tenant
            tenant = Tenant.objects.filter(booking_request=booking).first()
            if tenant:
                print(f"[+] Tenant '{tenant.full_name}' was saved to the DB.")
                if tenant.agreement_pdf:
                    print(f"[+] PDF Agreement was saved: {tenant.agreement_pdf.name}")
                else:
                    print("[-] PDF Agreement was NOT saved.")
            else:
                print("[-] Tenant was NOT created in the DB.")
                print("--- START HTML RESPONSE ---")
                print(response.content.decode())
                print("--- END HTML RESPONSE ---")
        else:
            print("[-] Form submission failed or redirected unexpectedly.")
            print(response.content.decode()[:500]) # Print snippet of response
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[-] Exception occurred during request: {e}")

    print("--- Test Completed ---")

if __name__ == "__main__":
    test_email_workflow()
