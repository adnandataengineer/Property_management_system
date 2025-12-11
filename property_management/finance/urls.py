from django.urls import path
from . import views

app_name = "finance"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("connect/", views.xero_start, name="xero_start"),
    path("xero/callback/", views.xero_callback, name="xero_callback"),
    path("disconnect/", views.xero_disconnect, name="xero_disconnect"),
    path("settings/update/", views.update_settings, name="update_settings"),
    path("reconcile/run/", views.run_reconciliation, name="run_reconciliation"),
    path("test/contacts/", views.test_contacts, name="test_contacts"),
    path("test/transactions/", views.test_bank_transactions, name="test_bank_transactions"),
]
