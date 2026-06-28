"""
Builds the monthly rent invoice (PDF + email) and sends it to a tenant.

Used by the `send_rent_reminders` management command to deliver the invoice and
bank/payment routing details a configurable number of days (default 10) before
the rent due date.
"""
from io import BytesIO
from decimal import Decimal

from django.conf import settings as django_settings
from django.core.mail import EmailMessage
from django.template.loader import get_template


def _money(value):
    """Format a Decimal/number as a 2dp string for display."""
    return f"{Decimal(str(value)):.2f}"


def build_invoice_context(booking, due_date, finance_settings):
    """Assemble the template/email context for a booking's rent invoice."""
    room = booking.room
    property_obj = room.property
    property_address = f"{property_obj.street_number} {property_obj.street_name}".strip()

    line_items = []
    rent = room.rent or Decimal("0")
    bills = room.bill_price or Decimal("0")

    if rent > 0:
        line_items.append({
            "description": f"Rent for {room.room_name} ({due_date.strftime('%B %Y')})",
            "amount": _money(rent),
        })
    if bills > 0:
        line_items.append({
            "description": "Utilities / Bills",
            "amount": _money(bills),
        })

    total = rent + bills
    payment_reference = f"{booking.full_name} - {room.room_name}"

    return {
        "company_name": getattr(django_settings, "COMPANY_NAME", "Property Management"),
        "invoice_reference": f"RENT-{booking.pk}-{due_date.strftime('%Y%m')}",
        "invoice_date": due_date.strftime("%B %d, %Y"),
        "due_date": due_date.strftime("%B %d, %Y"),
        "full_name": booking.full_name,
        "email": booking.email,
        "property_address": property_address,
        "room_name": room.room_name,
        "line_items": line_items,
        "total": _money(total),
        "total_decimal": total,
        "payment_reference": payment_reference,
        "bank": finance_settings,
    }


def generate_invoice_pdf(context):
    """Render the invoice PDF. Returns bytes, or None if generation failed."""
    try:
        from xhtml2pdf import pisa
        template = get_template("finance/pdf/rent_invoice.html")
        html = template.render(context)
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, encoding="UTF-8")
        if pdf.err:
            print(f"Invoice PDF generation had errors for {context.get('invoice_reference')}")
            return None
        return result.getvalue()
    except Exception as e:
        print(f"Error generating invoice PDF: {e}")
        return None


def build_email_body(context):
    """Plain-text email body with the invoice breakdown and bank details."""
    bank = context["bank"]
    lines = [
        f"Dear {context['full_name']},",
        "",
        f"Please find attached your invoice for the rent due on {context['due_date']}.",
        "",
        f"Property: {context['property_address']}",
        f"Room: {context['room_name']}",
        "",
        "Charges:",
    ]
    for item in context["line_items"]:
        lines.append(f"  - {item['description']}: €{item['amount']}")
    lines += [
        f"  Total Due: €{context['total']}",
        "",
        "Payment details (bank transfer):",
    ]
    if bank.bank_account_name:
        lines.append(f"  Account Name: {bank.bank_account_name}")
    if bank.bank_name:
        lines.append(f"  Bank: {bank.bank_name}")
    if bank.bank_iban:
        lines.append(f"  IBAN: {bank.bank_iban}")
    if bank.bank_bic:
        lines.append(f"  BIC / SWIFT: {bank.bank_bic}")
    if bank.bank_account_number:
        lines.append(f"  Account Number: {bank.bank_account_number}")
    if bank.bank_sort_code:
        lines.append(f"  Sort Code: {bank.bank_sort_code}")
    lines += [
        f"  Amount: €{context['total']}",
        f"  Reference: {context['payment_reference']}",
    ]
    if bank.payment_reference_note:
        lines += ["", bank.payment_reference_note]
    lines += [
        "",
        f"Please ensure payment reaches the account on or before {context['due_date']}.",
        "",
        "Best regards,",
        context["company_name"],
    ]
    return "\n".join(lines)


def send_invoice_email(booking, due_date, finance_settings):
    """
    Build and send the invoice email (body + PDF attachment) for a booking.

    Returns (sent: bool, message: str).
    """
    if not booking.email:
        return False, "no email address on booking"

    context = build_invoice_context(booking, due_date, finance_settings)
    body = build_email_body(context)

    email = EmailMessage(
        subject=f"{getattr(django_settings, 'EMAIL_SUBJECT_PREFIX', '')}Invoice - Rent due {context['due_date']}",
        body=body,
        from_email=django_settings.DEFAULT_FROM_EMAIL,
        to=[booking.email],
    )

    pdf_bytes = generate_invoice_pdf(context)
    if pdf_bytes:
        email.attach(
            f"Invoice_{context['invoice_reference']}.pdf",
            pdf_bytes,
            "application/pdf",
        )

    email.send(fail_silently=False)
    return True, "invoice attached" if pdf_bytes else "sent without PDF (generation failed)"
