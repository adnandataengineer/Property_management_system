import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "property_management.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Delete existing admin user if it exists
if User.objects.filter(username='admin').exists():
    User.objects.filter(username='admin').delete()
    print("Deleted existing admin user")

# Create new admin user
admin = User.objects.create_superuser(
    username='admin',
    email='admin@example.com',
    password='admin'
)

print("✅ Admin user created successfully!")
print("Username: admin")
print("Password: admin")
print("Email: admin@example.com")
