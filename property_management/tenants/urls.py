from django.urls import path
from .views import TenantListView, TenantDetailView

app_name = 'tenants'

urlpatterns = [
    path('', TenantListView.as_view(), name='tenant_list'),
    path('<int:pk>/', TenantDetailView.as_view(), name='tenant_detail'),
]