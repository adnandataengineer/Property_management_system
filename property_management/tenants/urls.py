from django.urls import path
from . import views

app_name = 'tenants'

urlpatterns = [
    path('onboarding/<int:booking_id>/', views.tenant_onboarding, name='onboarding'),
    # Fallback without ID if needed, though we prefer ID
    path('onboarding/', views.tenant_onboarding, name='onboarding_no_id'),
]