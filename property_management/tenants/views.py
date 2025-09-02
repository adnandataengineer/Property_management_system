from django.views.generic import ListView, DetailView
from .models import Tenant

class TenantListView(ListView):
    model = Tenant
    template_name = 'tenants/tenant_list.html'
    context_object_name = 'tenants'

class TenantDetailView(DetailView):
    model = Tenant
    template_name = 'tenants/tenant_detail.html'
    context_object_name = 'tenant'