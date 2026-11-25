import json
import logging

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from homepage.models import Payment, SiteSettings

from .gateways import GatewayError
from .models import BankAccount
from .services import (
    callback_token_valid, detect_network, gateway_status, manual_instructions,
    notify_finance_team, payment_target, start_mobile_payment, sync_payment_status,
)

logger = logging.getLogger(__name__)

STAFF_ROLES = ("super_admin", "admin", "manager", "accountant", "sales_agent")
MAX_RECEIPT_BYTES = 5 * 1024 * 1024
MAX_PUSH_ATTEMPTS = 5          # per payment per 15 minutes


def _get_payment_for_user(request, pk):
    payment = get_object_or_404(
        Payment.objects.select_related("customer", "booking__car", "schedule__car", "bank_account"),
        pk=pk,
    )
    user = request.user
    if payment.customer_id != user.id and getattr(user, "role", "") not in STAFF_ROLES:
        raise Http404  # don't reveal that the payment exists
    return payment


def _status_payload(payment):
    kind, obj, _car = payment_target(payment)
    detail_url = ""
    if kind == "booking":
        detail_url = reverse("homepage:booking_detail", args=[obj.pk])
    elif kind == "schedule":
        detail_url = reverse("homepage:schedule_detail", args=[obj.pk])
    return {
        "status": payment.status,
        "provider_status": payment.provider_status,
        "paid": payment.status == "success",
        "failed": payment.provider_status == "failed",
        "message": payment.failure_reason,
        "detail_url": detail_url,
    }


class ProofForm(forms.Form):
    METHOD_CHOICES = [
        ("mtn_momo", "MTN MoMo"),
        ("airtel_money", "Airtel Money"),
        ("bank_transfer", "Bank transfer"),
        ("cash", "Cash"),
    ]
    method = forms.ChoiceField(choices=METHOD_CHOICES)
    transaction_id = forms.CharField(max_length=100, required=False)
    payer_name = forms.CharField(max_length=150, required=False)
    bank_account = forms.ModelChoiceField(queryset=BankAccount.objects.filter(is_active=True), required=False)
    receipt = forms.ImageField(required=False)

    def clean_transaction_id(self):
        value = (self.cleaned_data.get("transaction_id") or "").strip()
        if value and not value.replace("-", "").replace(".", "").replace(" ", "").isalnum():
            raise forms.ValidationError("Transaction ID may contain letters, digits and dashes only.")
        return value.upper()

    def clean_receipt(self):
        f = self.cleaned_data.get("receipt")
        if f and f.size > MAX_RECEIPT_BYTES:
            raise forms.ValidationError("Receipt image must be 5 MB or smaller.")
        return f

    def clean(self):
        cd = super().clean()
        method = cd.get("method")
        if method in ("mtn_momo", "airtel_money", "bank_transfer"):
            if not cd.get("transaction_id") and not cd.get("receipt"):
                raise forms.ValidationError("Enter the transaction ID or upload a screenshot of the receipt.")
        return cd


@login_required
def checkout(request, pk):
    payment = _get_payment_for_user(request, pk)
    kind, obj, car = payment_target(payment)
    site = SiteSettings.objects.first()
    cover = None
    if car is not None:
        cover = car.photos.filter(is_cover=True).first() or car.photos.first()

    banks = list(BankAccount.objects.filter(is_active=True))
    if not banks and site and site.payment_account:
        banks = [BankAccount(bank_name="Company account", account_name=site.payment_account_name or "On Call Driver",
                             account_number=site.payment_account, brand_color="#1e5eff")]

    phone_network = detect_network(payment.phone_number)
    initial_method = payment.payment_method if payment.payment_method in ("mtn_momo", "airtel_money", "bank_transfer", "cash") else (phone_network or "mtn_momo")

    context = {
        "payment": payment,
        "kind": kind,
        "target": obj,
        "car": car,
        "cover_url": cover.photo.url if cover and cover.photo else "",
        "banks": banks,
        "live": gateway_status(),
        "manual": manual_instructions(payment, site),
        "initial_method": initial_method,
        "phone_local": ("0" + payment.phone_number[4:]) if payment.phone_number.startswith("+250") else payment.phone_number,
        "status_url": reverse("payment:status", args=[payment.pk]),
        "start_url": reverse("payment:start", args=[payment.pk]),
        "proof_url": reverse("payment:proof", args=[payment.pk]),
        "detail_url": _status_payload(payment)["detail_url"],
        "is_owner": payment.customer_id == request.user.id,
    }
    return render(request, "payment/checkout.html", context)


@login_required
@require_POST
def start(request, pk):
    payment = _get_payment_for_user(request, pk)
    if payment.customer_id != request.user.id:
        return JsonResponse({"ok": False, "error": "Only the customer can start this payment."}, status=403)

    attempts_key = f"pay_attempts:{payment.pk}"
    attempts = cache.get(attempts_key, 0)
    if attempts >= MAX_PUSH_ATTEMPTS:
        return JsonResponse({"ok": False, "error": "Too many attempts. Please wait 15 minutes or pay manually."}, status=429)
    cache.set(attempts_key, attempts + 1, 15 * 60)

    method = request.POST.get("method", "")
    phone = request.POST.get("phone", "")
    try:
        result = start_mobile_payment(payment, method, phone)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    except GatewayError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=502)
    except Exception:
        logger.exception("Payment start failed for %s", payment.payment_number)
        return JsonResponse({"ok": False, "error": "The payment service is unavailable right now. Please pay manually below."}, status=502)
    return JsonResponse({"ok": True, **result, **_status_payload(payment)})


@login_required
@require_GET
def status(request, pk):
    payment = _get_payment_for_user(request, pk)
    throttle_key = f"pay_status:{payment.pk}"
    if payment.status != "success" and not cache.get(throttle_key):
        cache.set(throttle_key, 1, 4)
        payment = sync_payment_status(payment, request=request)
        payment.refresh_from_db()
    return JsonResponse(_status_payload(payment))


@login_required
@require_POST
def proof(request, pk):
    payment = _get_payment_for_user(request, pk)
    if payment.customer_id != request.user.id:
        raise Http404
    if payment.status == "success":
        messages.info(request, "This payment is already confirmed.")
        return redirect("payment:checkout", pk=payment.pk)

    form = ProofForm(request.POST, request.FILES)
    if not form.is_valid():
        errors = " ".join(e for errs in form.errors.values() for e in errs)
        messages.error(request, errors or "Please check the payment details.")
        return redirect("payment:checkout", pk=payment.pk)

    cd = form.cleaned_data
    txn = cd["transaction_id"]
    if txn and Payment.objects.exclude(pk=payment.pk).filter(transaction_id__iexact=txn).exists():
        messages.error(request, "That transaction ID has already been used for another payment.")
        return redirect("payment:checkout", pk=payment.pk)

    payment.payment_method = cd["method"]
    if txn:
        payment.transaction_id = txn
    if cd.get("receipt"):
        payment.receipt_image = cd["receipt"]
    payment.payer_name = cd.get("payer_name") or payment.payer_name
    payment.bank_account = cd.get("bank_account") if cd["method"] == "bank_transfer" else None
    payment.provider_status = "awaiting_verification"
    payment.failure_reason = ""
    payment.save()

    notify_finance_team(
        payment,
        title=f"Verify payment {payment.payment_number}",
        message=f"{payment.customer.full_name} submitted {payment.get_payment_method_display()} proof "
                f"for {int(payment.amount):,} RWF (ref {payment.reference_code}{', txn ' + txn if txn else ''}).",
        link=request.build_absolute_uri(reverse("homepage:dashboard")),
    )
    messages.success(request, "Thanks! Your payment proof was submitted. Our finance team will verify it shortly.")
    return redirect("payment:checkout", pk=payment.pk)


def _find_payment_by_reference(*refs):
    for ref in refs:
        if ref:
            payment = Payment.objects.filter(provider_reference=str(ref)).first()
            if payment:
                return payment
    return None


@csrf_exempt
@require_POST
def mtn_callback(request, token):
    """MTN posts here when a request-to-pay completes. We re-query MTN rather than trust the body."""
    if not callback_token_valid(token):
        return HttpResponse(status=403)
    try:
        body = json.loads(request.body or b"{}")
    except ValueError:
        body = {}
    payment = _find_payment_by_reference(body.get("referenceId"), request.headers.get("X-Reference-Id"))
    if payment is None:
        payment = Payment.objects.filter(payment_number=body.get("externalId", "")).first()
    if payment is not None:
        sync_payment_status(payment)
    return HttpResponse(status=200)


@csrf_exempt
@require_POST
def airtel_callback(request, token):
    """Airtel posts here when a collection completes. We re-query Airtel rather than trust the body."""
    if not callback_token_valid(token):
        return HttpResponse(status=403)
    try:
        body = json.loads(request.body or b"{}")
    except ValueError:
        body = {}
    txn = body.get("transaction") or {}
    payment = _find_payment_by_reference(txn.get("id"))
    if payment is not None:
        sync_payment_status(payment)
    return HttpResponse(status=200)
