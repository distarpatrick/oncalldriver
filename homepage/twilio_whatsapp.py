import logging

from django.conf import settings

from .models import WhatsAppMessage

logger = logging.getLogger(__name__)


def _format_phone(phone_number):
    phone_number = (phone_number or "").strip().replace(" ", "")
    if not phone_number:
        return ""
    if phone_number.startswith("whatsapp:"):
        return phone_number
    return f"whatsapp:{phone_number}"


def _format_money(amount):
    if amount is None:
        return "0 RWF"
    try:
        return f"{int(amount):,} RWF"
    except (TypeError, ValueError):
        return f"{amount} RWF"


def _car_title(car):
    if not car:
        return "Selected vehicle"
    brand = getattr(getattr(car, "brand", None), "name", "") or ""
    parts = [str(part) for part in (getattr(car, "year", ""), brand, getattr(car, "model", "")) if part]
    return " ".join(parts) or getattr(car, "title", "Selected vehicle")


def _build_car_photo_url(request, car):
    if not car:
        return ""
    photo = car.photos.filter(is_cover=True).first() or car.photos.first()
    if not photo or not photo.photo:
        return ""
    try:
        photo_url = photo.photo.url
    except ValueError:
        return ""
    if request:
        return request.build_absolute_uri(photo_url)
    site_base_url = getattr(settings, "SITE_BASE_URL", "").rstrip("/")
    if site_base_url and photo_url.startswith("/"):
        return f"{site_base_url}{photo_url}"
    return photo_url


class TwilioWhatsAppService:
    def __init__(self):
        self.account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
        self.auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
        self.from_number = getattr(settings, "TWILIO_WHATSAPP_NUMBER", "")
        self.company_phone = getattr(settings, "COMPANY_PHONE_NUMBER", "0791273368")

    def is_configured(self):
        placeholder_values = {"ACxxx", "your-token", "whatsapp:+14155238886"}
        return all([self.account_sid, self.auth_token, self.from_number]) and not any(
            value in placeholder_values
            for value in (self.account_sid, self.auth_token, self.from_number)
        )

    def send_message(self, to_number, body, media_url=None, message_type="custom_message", metadata=None, payment=None, booking=None, visit=None):
        metadata = metadata or {}
        clean_to_number = _format_phone(to_number)
        if not clean_to_number:
            self._log_failed("", body, message_type, "Missing recipient phone number", metadata, payment, booking, visit)
            return False

        if not self.is_configured():
            self._log_failed(clean_to_number, body, message_type, "Twilio WhatsApp credentials are not configured", metadata, payment, booking, visit)
            return False

        try:
            from twilio.rest import Client
        except ImportError:
            self._log_failed(clean_to_number, body, message_type, "The twilio package is not installed", metadata, payment, booking, visit)
            return False

        try:
            client = Client(self.account_sid, self.auth_token)
            kwargs = {
                "from_": _format_phone(self.from_number),
                "to": clean_to_number,
                "body": body,
            }
            if media_url:
                kwargs["media_url"] = [media_url]
            message = client.messages.create(**kwargs)
            WhatsAppMessage.objects.create(
                phone_number=clean_to_number.replace("whatsapp:", ""),
                message_type=message_type,
                status="sent",
                message_id=getattr(message, "sid", None),
                content=body,
                metadata={**metadata, "provider": "twilio", "media_url": media_url or ""},
                payment=payment,
                booking=booking,
                visit=visit,
            )
            return True
        except Exception as exc:
            logger.exception("Twilio WhatsApp send failed")
            self._log_failed(clean_to_number, body, message_type, str(exc), metadata, payment, booking, visit)
            return False

    def _log_failed(self, phone_number, body, message_type, error, metadata, payment=None, booking=None, visit=None):
        WhatsAppMessage.objects.create(
            phone_number=phone_number.replace("whatsapp:", ""),
            message_type=message_type,
            status="failed",
            content=body,
            metadata={**metadata, "provider": "twilio", "error": error},
            payment=payment,
            booking=booking,
            visit=visit,
        )
        logger.error("Twilio WhatsApp failed: %s", error)

    def send_account_welcome(self, user):
        body = (
            f"*Welcome to On Call Driver, {user.full_name}!*\n\n"
            "Your customer account is ready.\n\n"
            "*What you can do now:*\n"
            "- Browse available cars\n"
            "- Book a car with payment verification\n"
            "- Schedule a car visit\n"
            "- Track bookings and invoices from your profile\n\n"
            f"Need help? Contact us at {self.company_phone}."
        )
        return self.send_message(
            user.phone,
            body,
            message_type="custom_message",
            metadata={"event": "account_created", "user_id": str(user.id), "customer_name": user.full_name},
        )

    def send_payment_confirmation(self, payment, request=None):
        booking = payment.booking
        visit = payment.schedule
        car = booking.car if booking else visit.car if visit else None
        reference = booking.booking_number if booking else visit.schedule_number if visit else payment.payment_number
        body = (
            "*Payment Confirmed - On Call Driver*\n\n"
            f"Hello {payment.customer.full_name}, your payment has been confirmed.\n\n"
            "*Payment Details:*\n"
            f"- Reference: {reference}\n"
            f"- Payment No: {payment.payment_number}\n"
            f"- Amount: {_format_money(payment.amount)}\n"
            f"- Method: {payment.get_payment_method_display()}\n"
            f"- Vehicle: {_car_title(car)}\n\n"
        )
        if booking:
            body += (
                "*Booking Status: Confirmed*\n"
                f"- Paid: {_format_money(booking.amount_paid)}\n"
                f"- Balance: {_format_money(booking.remaining_balance)}\n\n"
            )
        elif visit:
            body += (
                "*Visit Status: Confirmed*\n"
                f"- Date: {visit.visit_date:%d %B %Y}\n"
                f"- Time: {visit.visit_time:%H:%M}\n"
                f"- Location: {visit.location}\n\n"
            )
        body += f"Thank you for choosing On Call Driver. Questions? Contact {self.company_phone}."
        return self.send_message(
            payment.customer.phone,
            body,
            media_url=None,
            message_type="payment_confirmation",
            metadata={
                "event": "payment_confirmed",
                "payment_id": str(payment.id),
                "reference": reference,
                "car_id": str(car.id) if car else "",
                "car_title": _car_title(car),
                "media_skipped": True,
            },
            payment=payment,
            booking=booking,
            visit=visit,
        )


twilio_whatsapp_service = TwilioWhatsAppService()
