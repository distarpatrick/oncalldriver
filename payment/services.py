"""
Payment business logic shared by the checkout, provider callbacks and the
staff dashboard.  ``mark_payment_successful`` is the single place where a
payment becomes "paid" and the related booking / visit is confirmed.
"""
import logging
import re
from urllib.parse import quote

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .gateways import GatewayError, get_gateway

logger = logging.getLogger(__name__)

MOBILE_METHODS = ("mtn_momo", "airtel_money")
FINANCE_ROLES = ("super_admin", "admin", "accountant", "manager")

# Rwanda mobile prefixes: MTN 078/079, Airtel 072/073
NETWORK_PREFIXES = {
    "mtn_momo": ("+25078", "+25079"),
    "airtel_money": ("+25072", "+25073"),
}


def normalize_msisdn(phone):
    phone = re.sub(r"[\s\-().]", "", phone or "")
    if phone.startswith("00250"):
        phone = "+" + phone[2:]
    elif phone.startswith("250"):
        phone = "+" + phone
    elif phone.startswith("07"):
        phone = "+250" + phone[1:]
    return phone if re.fullmatch(r"\+2507\d{8}", phone) else ""


def detect_network(phone):
    phone = normalize_msisdn(phone)
    for method, prefixes in NETWORK_PREFIXES.items():
        if phone.startswith(prefixes):
            return method
    return ""


def payment_target(payment):
    """Return (kind, object, car) for the thing this payment is for."""
    if payment.booking_id:
        return "booking", payment.booking, payment.booking.car
    if payment.schedule_id:
        return "schedule", payment.schedule, payment.schedule.car
    return "", None, None


def manual_instructions(payment, site):
    """USSD / MoMoPay strings for paying without the API (manual mode)."""
    amount = int(payment.amount)
    mtn_code = (getattr(site, "payment_mtn_code", "") or "").strip()
    mtn_phone = normalize_msisdn(getattr(site, "payment_phone", ""))
    airtel_phone = normalize_msisdn(getattr(site, "payment_airtel_phone", "")) or mtn_phone

    def local(msisdn):
        return "0" + msisdn[4:] if msisdn else ""

    mtn_ussd = f"*182*8*1*{mtn_code}*{amount}#" if mtn_code else (
        f"*182*1*1*{local(mtn_phone)}*{amount}#" if mtn_phone else "*182#")
    airtel_ussd = "*500#"
    return {
        "mtn_ussd": mtn_ussd,
        "mtn_ussd_href": "tel:" + quote(mtn_ussd, safe="*"),
        "mtn_code": mtn_code,
        "mtn_phone": local(mtn_phone),
        "airtel_ussd": airtel_ussd,
        "airtel_ussd_href": "tel:" + quote(airtel_ussd, safe="*"),
        "airtel_phone": local(airtel_phone),
        "account_name": getattr(site, "payment_account_name", "") or "On Call Driver",
    }


def start_mobile_payment(payment, method, phone):
    """
    Send a push prompt via MTN/Airtel. Returns a dict for the JSON response.
    Raises ValueError for user errors, GatewayError for provider errors.
    """
    if payment.status == "success":
        raise ValueError("This payment has already been completed.")
    if method not in MOBILE_METHODS:
        raise ValueError("Choose MTN MoMo or Airtel Money.")
    msisdn = normalize_msisdn(phone)
    if not msisdn:
        raise ValueError("Enter a valid Rwandan mobile number, e.g. 078 123 4567.")
    network = detect_network(msisdn)
    if network != method:
        label = "MTN (078/079)" if method == "mtn_momo" else "Airtel (072/073)"
        raise ValueError(f"That number is not an {label} number.")

    gateway = get_gateway(method)
    payment.payment_method = method
    payment.phone_number = msisdn

    if not gateway or not gateway.configured:
        payment.save(update_fields=["payment_method", "phone_number", "updated_at"])
        return {"mode": "manual"}

    kind, obj, car = payment_target(payment)
    label = getattr(obj, "booking_number", None) or getattr(obj, "schedule_number", None) or payment.payment_number
    result = gateway.request_to_pay(
        amount=payment.amount,
        msisdn=msisdn,
        external_id=payment.payment_number,
        payer_message=f"On Call Driver {label}",
        payee_note=f"{payment.get_purpose_display()} {payment.reference_code}",
    )
    payment.provider_reference = result.reference
    payment.provider_status = "awaiting_approval"
    payment.failure_reason = ""
    payment.provider_payload = {"initiated_at": timezone.now().isoformat(), "method": method}
    payment.save(update_fields=["payment_method", "phone_number", "provider_reference",
                                "provider_status", "failure_reason", "provider_payload", "updated_at"])
    return {"mode": "push", "status": "pending"}


def sync_payment_status(payment, request=None):
    """Ask the provider for the latest status of a pushed payment."""
    if payment.status == "success" or not payment.provider_reference:
        return payment
    if payment.provider_status not in ("awaiting_approval", "initiated"):
        return payment
    gateway = get_gateway(payment.payment_method)
    if not gateway or not gateway.configured:
        return payment
    try:
        result = gateway.get_status(payment.provider_reference)
    except GatewayError as exc:
        logger.warning("Status check failed for %s: %s", payment.payment_number, exc)
        return payment
    except Exception:  # network errors etc.
        logger.exception("Status check crashed for %s", payment.payment_number)
        return payment

    if result.status == "successful":
        if result.provider_txn_id:
            payment.transaction_id = result.provider_txn_id
            payment.save(update_fields=["transaction_id"])
        mark_payment_successful(payment, processed_by=None, request=request, source=payment.payment_method)
    elif result.status == "failed":
        payment.provider_status = "failed"
        payment.failure_reason = result.message or "The payment was declined or timed out."
        payment.save(update_fields=["provider_status", "failure_reason", "updated_at"])
    return payment


def notify_finance_team(payment, title, message, link=""):
    from homepage.models import CustomUser, Notification
    staff = CustomUser.objects.filter(role__in=FINANCE_ROLES, is_active=True)
    Notification.objects.bulk_create([
        Notification(user=u, title=title, message=message, notif_type="payment", link=link)
        for u in staff
    ])


def mark_payment_successful(payment, processed_by=None, request=None, source="staff"):
    """Idempotently mark a payment as paid and confirm its booking / visit."""
    from homepage.models import AuditLog, Notification, Payment

    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status == "success":
            return payment, False
        payment.status = "success"
        payment.provider_status = "successful"
        payment.failure_reason = ""
        payment.paid_at = timezone.now()
        if processed_by is not None:
            payment.processed_by = processed_by
        payment.save()

        if payment.booking_id:
            booking = payment.booking
            if booking.status == "pending":
                booking.status = "confirmed"
                if processed_by is not None:
                    booking.handled_by = processed_by
                booking.save()
        if payment.schedule_id:
            schedule = payment.schedule
            schedule.fee_paid = True
            if schedule.status == "pending":
                schedule.status = "confirmed"
            if processed_by is not None:
                schedule.confirmed_by = processed_by
            schedule.save()

        AuditLog.objects.create(
            user=processed_by,
            action="updated",
            model_affected="Payment",
            object_id=str(payment.pk),
            description=f"Payment {payment.payment_number} marked paid via {source} — {payment.amount} RWF",
            ip_address=(request.META.get("REMOTE_ADDR") if request else None),
        )

    # Side effects outside the transaction
    try:
        from homepage.views import _ensure_invoice_for_payment
        _ensure_invoice_for_payment(payment, processed_by, request=request)
    except Exception:
        logger.exception("Invoice generation failed for %s", payment.payment_number)

    Notification.objects.create(
        user=payment.customer,
        title="Payment received",
        message=f"We received {int(payment.amount):,} RWF for {payment.get_purpose_display()} "
                f"(ref {payment.reference_code}). Thank you!",
        notif_type="payment",
    )
    try:
        from homepage.twilio_whatsapp import twilio_whatsapp_service
        twilio_whatsapp_service.send_payment_confirmation(payment, request=request)
    except Exception:
        logger.exception("WhatsApp confirmation failed for %s", payment.payment_number)
    return payment, True


def gateway_status():
    """Which mobile-money APIs are live (for the checkout UI)."""
    return {m: bool(get_gateway(m) and get_gateway(m).configured) for m in MOBILE_METHODS}


def callback_token_valid(token):
    import hmac
    expected = getattr(settings, "PAYMENT_CALLBACK_TOKEN", "") or ""
    return bool(expected) and hmac.compare_digest(str(token), expected)
