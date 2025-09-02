from django.conf import settings
from django.contrib import messages
from django.core.mail import mail_admins, send_mail
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import ListView, DetailView

from .forms import BookingRequestForm
from .models import Property



class PropertyListView(ListView):
    model = Property
    template_name = "properties/property_list.html"
    context_object_name = "properties"

    def get_queryset(self):
        qs = Property.objects.filter(is_available=True)
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(street_name__icontains=q) |
                Q(street_number__icontains=q) |
                Q(id__icontains=q)
            )
        return qs


class PropertyDetailView(DetailView):
    model = Property
    template_name = "properties/property_detail.html"
    context_object_name = "property"

    def get_queryset(self):
        # 404 for unavailable properties
        return Property.objects.filter(is_available=True)


def booking_request_create(request, pk):
    # Only allow booking if the property is available
    prop = get_object_or_404(Property, pk=pk, is_available=True)
    type_label = (prop.get_type_display() or "-") if hasattr(prop, "get_type_display") else (prop.type or "-")


    if request.method == "POST":
        # pass 'property' for duplicate-check validation in the form
        form = BookingRequestForm(request.POST, property=prop)
        if form.is_valid():
            br = form.save(commit=False)
            br.property = prop
            # UI collects only start_date; keep DB consistent
            br.end_date = br.start_date
            br.save()

            # Admin deep link
            try:
                admin_change_url = request.build_absolute_uri(
                    reverse("admin:properties_bookingrequest_change", args=[br.pk])
                )
            except Exception:
                admin_change_url = "(admin URL unavailable)"

            # --- Admin email (branded) ---
            subject = f"New booking request — {prop}"
            text_message = (
                "Smart Home Management System\n\n"
                f"Property: {prop}\n"
                f"Type: {type_label}\n"
                f"Name: {br.full_name}\n"
                f"Email: {br.email}\n"
                f"Phone: {br.phone or '-'}\n"
                f"Check-in: {br.start_date}\n"
                "Notes:\n"
                f"{br.notes or ''}\n\n"
                f"Admin: {admin_change_url}"
            )
            html_message = f"""
            <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:640px">
              <h2 style="margin:0 0 12px">Smart Home Management System</h2>
              <p style="margin:0 0 16px;color:#555">You have a new booking request.</p>
              <table style="border-collapse:collapse;width:100%;margin-bottom:16px">
                <tr><td style="padding:8px;border:1px solid #eee"><strong>Property</strong></td><td style="padding:8px;border:1px solid #eee">{prop}</td></tr>
                <tr><td style="padding:8px;border:1px solid #eee"><strong>Type</strong></td><td style="padding:8px;border:1px solid #eee">{type_label}</td></tr>
                <tr><td style="padding:8px;border:1px solid #eee"><strong>Name</strong></td><td style="padding:8px;border:1px solid #eee">{br.full_name}</td></tr>
                <tr><td style="padding:8px;border:1px solid #eee"><strong>Email</strong></td><td style="padding:8px;border:1px solid #eee">{br.email}</td></tr>
                <tr><td style="padding:8px;border:1px solid #eee"><strong>Phone</strong></td><td style="padding:8px;border:1px solid #eee">{br.phone or '—'}</td></tr>
                <tr><td style="padding:8px;border:1px solid #eee"><strong>Check-in</strong></td><td style="padding:8px;border:1px solid #eee">{br.start_date}</td></tr>
                <tr><td style="padding:8px;border:1px solid #eee"><strong>Notes</strong></td><td style="padding:8px;border:1px solid #eee">{(br.notes or '').replace('\n','<br>')}</td></tr>
              </table>
              <p style="margin:0 0 8px">
                <a href="{admin_change_url}" style="background:#0d6efd;color:#fff;padding:10px 14px;border-radius:6px;text-decoration:none">Open in Admin</a>
              </p>
            </div>
            """
            mail_admins(
                subject=subject,
                message=text_message,
                html_message=html_message,
                fail_silently=False,
            )

            # --- Confirmation email to requester ---
            user_subject = f"We received your booking request — {prop}"
            user_text = (
                "Smart Home Management System\n\n"
                "Thanks for your request. Here are the details we received:\n\n"
                f"Property: {prop}\n"
                f"Type: {type_label}\n"
                f"Name: {br.full_name}\n"
                f"Email: {br.email}\n"
                f"Phone: {br.phone or '-'}\n"
                f"Check-in: {br.start_date}\n"
                f"Notes:\n{br.notes or ''}\n\n"
                "Our team will review and get back to you shortly.\n"
                "— Smart Home Management"
            )
            user_html = f"""
            <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:640px">
              <h2 style="margin:0 0 12px">Smart Home Management System</h2>
              <p style="margin:0 0 16px;color:#555">Thanks for your request. Here are the details we received:</p>
              <table style="border-collapse:collapse;width:100%;margin-bottom:16px">
                <tr><td style="padding:8px;border:1px solid #eee"><strong>Property</strong></td><td style="padding:8px;border:1px solid #eee">{prop}</td></tr>
                <tr><td style="padding:8px;border:1px solid #eee"><strong>Type</strong></td><td style="padding:8px;border:1px solid #eee">{type_label}</td></tr>
                <tr><td style="padding:8px;border:1px solid #eee"><strong>Name</strong></td><td style="padding:8px;border:1px solid #eee">{br.full_name}</td></tr>
                <tr><td style="padding:8px;border:1px solid #eee"><strong>Email</strong></td><td style="padding:8px;border:1px solid #eee">{br.email}</td></tr>
                <tr><td style="padding:8px;border:1px solid #eee"><strong>Phone</strong></td><td style="padding:8px;border:1px solid #eee">{br.phone or '—'}</td></tr>
                <tr><td style="padding:8px;border:1px solid #eee"><strong>Check-in</strong></td><td style="padding:8px;border:1px solid #eee">{br.start_date}</td></tr>
                <tr><td style="padding:8px;border:1px solid #eee"><strong>Notes</strong></td><td style="padding:8px;border:1px solid #eee">{(br.notes or '').replace('\n','<br>')}</td></tr>
              </table>
              <p style="margin:0;color:#666">We’ll email you when it’s approved or if we need more info.</p>
            </div>
            """
            send_mail(
                subject=user_subject,
                message=user_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[br.email],
                fail_silently=True,
                html_message=user_html,
            )

            messages.success(request, "Thanks! Your booking request has been submitted.")
            return redirect("properties:detail", pk=prop.pk)
    else:
        # pass 'property' on GET too (keeps the form consistent)
        form = BookingRequestForm(property=prop)

    return render(request, "properties/booking_form.html", {"form": form, "property": prop})
