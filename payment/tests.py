from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from homepage.models import Booking, Car, CarBrand, CompanyCarOwner, CustomUser, Payment

from .gateways import GatewayResult
from .models import BankAccount
from .services import detect_network, mark_payment_successful, normalize_msisdn

LIVE_MTN = {
    "MTN": {"BASE_URL": "https://example.test", "SUBSCRIPTION_KEY": "k", "API_USER": "u",
            "API_KEY": "s", "ENVIRONMENT": "sandbox", "CURRENCY": "RWF", "CALLBACK_URL": ""},
    "AIRTEL": {},
}


class PaymentFlowTests(TestCase):
    def setUp(self):
        self.customer = CustomUser.objects.create_user(
            email="buyer@example.test", password="Sup3r-Secret-pw", full_name="Test Buyer",
            phone="+250781234567", role="customer",
        )
        self.other = CustomUser.objects.create_user(
            email="other@example.test", password="Sup3r-Secret-pw", full_name="Other", phone="+250791111111",
        )
        self.accountant = CustomUser.objects.create_user(
            email="finance@example.test", password="Sup3r-Secret-pw", full_name="Finance",
            phone="+250722222222", role="accountant",
        )
        owner = CompanyCarOwner.objects.create(full_name="Owner")
        brand = CarBrand.objects.create(name="Toyota")
        self.car = Car.objects.create(
            owner=owner, title="Toyota RAV4 2020", brand=brand, model="RAV4", year=2020, condition="new",
            color="White", transmission="automatic", fuel_type="petrol", registration_plate="RAD123A",
            price=Decimal("20000000"), scheduling_fee=Decimal("5000"), province="Kigali",
            district="Gasabo", description="Clean", status="available",
        )
        BankAccount.objects.create(bank_name="Bank of Kigali", account_name="On Call Driver", account_number="000400012345")

    def _book(self):
        self.client.force_login(self.customer)
        resp = self.client.post(
            reverse("homepage:book_car", args=[self.car.pk]),
            {"full_name": "Test Buyer", "phone": "078 123 4567", "payment_type": "half", "payment_method": "mtn_momo"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        return Payment.objects.get(booking__car=self.car), resp.json()

    def test_phone_helpers(self):
        self.assertEqual(normalize_msisdn("078 123 4567"), "+250781234567")
        self.assertEqual(normalize_msisdn("250731234567"), "+250731234567")
        self.assertEqual(normalize_msisdn("12345"), "")
        self.assertEqual(detect_network("0781234567"), "mtn_momo")
        self.assertEqual(detect_network("+250731234567"), "airtel_money")

    def test_booking_redirects_to_checkout_with_server_side_amount(self):
        payment, data = self._book()
        self.assertEqual(data["detail_url"], reverse("payment:checkout", args=[payment.pk]))
        self.assertEqual(payment.amount, Decimal("10000000"))  # 50% computed on the server
        self.assertTrue(payment.reference_code.startswith("OCD-"))
        self.assertEqual(payment.booking.status, "pending")
        page = self.client.get(data["detail_url"])
        self.assertContains(page, payment.reference_code)
        self.assertContains(page, "Bank of Kigali")

    def test_other_users_cannot_see_checkout(self):
        payment, _ = self._book()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("payment:checkout", args=[payment.pk])).status_code, 404)
        self.client.logout()
        resp = self.client.get(reverse("payment:checkout", args=[payment.pk]))
        self.assertEqual(resp.status_code, 302)

    def test_manual_proof_and_duplicate_transaction_rejected(self):
        payment, _ = self._book()
        url = reverse("payment:proof", args=[payment.pk])
        self.client.post(url, {"method": "mtn_momo", "transaction_id": "ABC123456"})
        payment.refresh_from_db()
        self.assertEqual(payment.provider_status, "awaiting_verification")
        self.assertEqual(payment.transaction_id, "ABC123456")
        self.assertEqual(payment.status, "pending")

        # Re-using the same transaction ID on another payment is blocked
        other_payment = Payment.objects.create(customer=self.customer, amount=5000, payment_method="mtn_momo",
                                               purpose="scheduling_fee")
        self.client.post(reverse("payment:proof", args=[other_payment.pk]), {"method": "mtn_momo", "transaction_id": "abc123456"})
        other_payment.refresh_from_db()
        self.assertEqual(other_payment.transaction_id, "")

    def test_proof_requires_reference_or_receipt(self):
        payment, _ = self._book()
        self.client.post(reverse("payment:proof", args=[payment.pk]), {"method": "bank_transfer"})
        payment.refresh_from_db()
        self.assertEqual(payment.provider_status, "")

    def test_start_without_api_keys_falls_back_to_manual(self):
        payment, _ = self._book()
        resp = self.client.post(reverse("payment:start", args=[payment.pk]), {"method": "mtn_momo", "phone": "0781234567"})
        self.assertEqual(resp.json()["mode"], "manual")

    def test_start_rejects_wrong_network(self):
        payment, _ = self._book()
        resp = self.client.post(reverse("payment:start", args=[payment.pk]), {"method": "airtel_money", "phone": "0781234567"})
        self.assertEqual(resp.status_code, 400)

    @override_settings(PAYMENTS=LIVE_MTN)
    def test_mtn_push_and_status_marks_booking_paid(self):
        payment, _ = self._book()
        with mock.patch("payment.gateways.MTNMoMoGateway.request_to_pay",
                        return_value=GatewayResult(status="pending", reference="ref-1")):
            resp = self.client.post(reverse("payment:start", args=[payment.pk]), {"method": "mtn_momo", "phone": "0781234567"})
        self.assertEqual(resp.json()["mode"], "push")
        payment.refresh_from_db()
        self.assertEqual(payment.provider_status, "awaiting_approval")

        with mock.patch("payment.gateways.MTNMoMoGateway.get_status",
                        return_value=GatewayResult(status="successful", reference="ref-1", provider_txn_id="99887766")):
            data = self.client.get(reverse("payment:status", args=[payment.pk])).json()
        self.assertTrue(data["paid"])
        payment.refresh_from_db()
        self.assertEqual(payment.transaction_id, "99887766")
        self.assertEqual(payment.booking.status, "confirmed")
        self.assertTrue(hasattr(payment, "invoice"))

    @override_settings(PAYMENT_CALLBACK_TOKEN="secret-token")
    def test_callback_requires_token(self):
        bad = self.client.post(reverse("payment:mtn_callback", args=["wrong"]), "{}", content_type="application/json")
        self.assertEqual(bad.status_code, 403)
        ok = self.client.post(reverse("payment:mtn_callback", args=["secret-token"]), "{}", content_type="application/json")
        self.assertEqual(ok.status_code, 200)

    def test_staff_confirmation_is_idempotent(self):
        payment, _ = self._book()
        _, changed = mark_payment_successful(payment, processed_by=self.accountant)
        self.assertTrue(changed)
        _, changed_again = mark_payment_successful(payment, processed_by=self.accountant)
        self.assertFalse(changed_again)
        booking = Booking.objects.get(pk=payment.booking_id)
        self.assertEqual(booking.status, "confirmed")


class SecurityTests(TestCase):
    def test_security_headers_present(self):
        resp = self.client.get(reverse("homepage:index"))
        self.assertIn("Content-Security-Policy", resp.headers)
        self.assertEqual(resp.headers.get("X-Frame-Options"), "DENY")

    def test_login_rate_limited(self):
        url = reverse("homepage:auth")
        for _ in range(6):
            self.client.post(url, {"action": "login", "email": "nobody@example.test", "password": "wrong"})
        resp = self.client.post(url, {"action": "login", "email": "nobody@example.test", "password": "wrong"}, follow=True)
        self.assertContains(resp, "Too many failed sign-in attempts")
