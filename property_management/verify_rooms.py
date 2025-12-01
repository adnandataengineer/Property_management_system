import os
import django
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "property_management.settings")
django.setup()

from properties.models import Property, Room, CommonArea, BookingRequest
from django.contrib.auth import get_user_model

def verify():
    print("Starting verification...")
    
    # Clean up
    Property.objects.all().delete()
    
    # Create Property
    prop = Property.objects.create(
        street_number="123",
        street_name="Test St",
        is_available=True,
        rent=0 # Property rent is now irrelevant/sum of rooms
    )
    print(f"Created property: {prop}")
    
    # Create Rooms
    r1 = Room.objects.create(
        property=prop,
        room_name="Room 1",
        room_type=Property.UnitType.PRIVATE_SINGLE,
        rent=500,
        is_available=True
    )
    print(f"Created room: {r1}")
    
    r2 = Room.objects.create(
        property=prop,
        room_name="Room 2",
        room_type=Property.UnitType.TWIN_ROOM,
        rent=800,
        is_available=True,
        has_twin_beds=True
    )
    print(f"Created room: {r2}")
    
    r3 = Room.objects.create(
        property=prop,
        room_name="Room 3",
        room_type=Property.UnitType.ENSUITE_DOUBLE,
        rent=1000,
        is_available=False # Unavailable
    )
    print(f"Created room: {r3}")
    
    # Create Common Area
    ca = CommonArea.objects.create(
        property=prop,
        name="Kitchen",
        description="Shared kitchen"
    )
    print(f"Created common area: {ca}")
    
    # Verify available room count
    count = prop.get_available_room_count()
    print(f"Available room count: {count} (Expected: 2)")
    assert count == 2
    
    # Verify Booking Request
    br = BookingRequest.objects.create(
        room=r1,
        full_name="John Doe",
        email="john@example.com",
        start_date=date.today(),
        end_date=date.today()
    )
    print(f"Created booking request: {br}")
    print(f"Booking request property: {br.property}")
    assert br.property == prop
    
    print("Verification successful!")

if __name__ == "__main__":
    verify()
