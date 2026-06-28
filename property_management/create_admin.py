"""
Create (or reset) the Django superuser from environment variables.

Never hard-code admin credentials. Provide them via the environment:

    DJANGO_SUPERUSER_USERNAME
    DJANGO_SUPERUSER_EMAIL
    DJANGO_SUPERUSER_PASSWORD

Usage:
    DJANGO_SUPERUSER_USERNAME=admin \
    DJANGO_SUPERUSER_EMAIL=you@example.com \
    DJANGO_SUPERUSER_PASSWORD='a-strong-password' \
    python create_admin.py
"""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "property_management.settings")
django.setup()

from django.contrib.auth import get_user_model

username = os.getenv("DJANGO_SUPERUSER_USERNAME")
email = os.getenv("DJANGO_SUPERUSER_EMAIL", "")
password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

if not username or not password:
    sys.exit(
        "Refusing to create an admin without credentials. Set "
        "DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD in the environment."
    )

User = get_user_model()

user, created = User.objects.get_or_create(
    username=username,
    defaults={"email": email},
)
user.email = email or user.email
user.is_staff = True
user.is_superuser = True
user.set_password(password)
user.save()

print(f"{'Created' if created else 'Updated'} superuser '{username}'.")
