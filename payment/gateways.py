"""
Mobile-money gateway clients for Rwanda.

* MTN MoMo  — MTN MoMo Open API, Collection product ("Request to Pay").
               https://momodeveloper.mtn.com
* Airtel    — Airtel Africa Open API, Collection ("USSD push").
               https://developers.airtel.africa

Both gateways send a payment prompt to the customer's phone; the customer
approves it with their PIN.  Final status is always read back from the
provider (never trusted from a browser or an unsigned callback body).

When credentials are not configured, the gateway reports ``configured=False``
and the checkout falls back to the manual flow (USSD/MoMoPay code + proof).
"""
import logging
import uuid
from dataclasses import dataclass, field

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

TIMEOUT = 20  # seconds


class GatewayError(Exception):
    pass


@dataclass
class GatewayResult:
    status: str                      # "pending" | "successful" | "failed"
    reference: str = ""
    message: str = ""
    provider_txn_id: str = ""
    raw: dict = field(default_factory=dict)


def _cfg(name):
    return (getattr(settings, "PAYMENTS", {}) or {}).get(name, {})


class MTNMoMoGateway:
    method = "mtn_momo"
    label = "MTN MoMo"

    def __init__(self):
        c = _cfg("MTN")
        self.base_url = (c.get("BASE_URL") or "https://sandbox.momodeveloper.mtn.com").rstrip("/")
        self.subscription_key = c.get("SUBSCRIPTION_KEY", "")
        self.api_user = c.get("API_USER", "")
        self.api_key = c.get("API_KEY", "")
        self.environment = c.get("ENVIRONMENT", "sandbox")
        self.currency = c.get("CURRENCY", "RWF")
        self.callback_url = c.get("CALLBACK_URL", "")

    @property
    def configured(self):
        return bool(self.subscription_key and self.api_user and self.api_key)

    def _token(self):
        key = f"mtn_momo_token:{self.api_user}"
        token = cache.get(key)
        if token:
            return token
        resp = requests.post(
            f"{self.base_url}/collection/token/",
            auth=(self.api_user, self.api_key),
            headers={"Ocp-Apim-Subscription-Key": self.subscription_key},
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            raise GatewayError(f"MTN token request failed ({resp.status_code})")
        data = resp.json()
        token = data["access_token"]
        cache.set(key, token, max(int(data.get("expires_in", 3600)) - 60, 60))
        return token

    def _headers(self):
        return {
            "Authorization": f"Bearer {self._token()}",
            "X-Target-Environment": self.environment,
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json",
        }

    def request_to_pay(self, *, amount, msisdn, external_id, payer_message, payee_note):
        reference = str(uuid.uuid4())
        headers = self._headers()
        headers["X-Reference-Id"] = reference
        if self.callback_url.startswith("https://"):
            headers["X-Callback-Url"] = self.callback_url
        body = {
            "amount": str(int(amount)),
            "currency": self.currency,
            "externalId": external_id,
            "payer": {"partyIdType": "MSISDN", "partyId": msisdn.lstrip("+")},
            "payerMessage": payer_message[:160],
            "payeeNote": payee_note[:160],
        }
        resp = requests.post(
            f"{self.base_url}/collection/v1_0/requesttopay",
            json=body, headers=headers, timeout=TIMEOUT,
        )
        if resp.status_code != 202:
            logger.warning("MTN requesttopay rejected: %s %s", resp.status_code, resp.text[:300])
            raise GatewayError("MTN MoMo could not send the payment prompt. Check the number and try again.")
        return GatewayResult(status="pending", reference=reference, message="Payment prompt sent.")

    def get_status(self, reference):
        resp = requests.get(
            f"{self.base_url}/collection/v1_0/requesttopay/{reference}",
            headers=self._headers(), timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            raise GatewayError(f"MTN status lookup failed ({resp.status_code})")
        data = resp.json()
        state = (data.get("status") or "").upper()
        status = {"SUCCESSFUL": "successful", "FAILED": "failed", "REJECTED": "failed",
                  "TIMEOUT": "failed"}.get(state, "pending")
        reason = data.get("reason")
        if isinstance(reason, dict):
            reason = reason.get("message") or reason.get("code")
        return GatewayResult(
            status=status, reference=reference,
            provider_txn_id=data.get("financialTransactionId", "") or "",
            message=str(reason or ""), raw=data,
        )


class AirtelMoneyGateway:
    method = "airtel_money"
    label = "Airtel Money"

    STATUS_MAP = {"TS": "successful", "TF": "failed", "TE": "failed", "TA": "pending", "TIP": "pending"}

    def __init__(self):
        c = _cfg("AIRTEL")
        self.base_url = (c.get("BASE_URL") or "https://openapiuat.airtel.africa").rstrip("/")
        self.client_id = c.get("CLIENT_ID", "")
        self.client_secret = c.get("CLIENT_SECRET", "")
        self.country = c.get("COUNTRY", "RW")
        self.currency = c.get("CURRENCY", "RWF")

    @property
    def configured(self):
        return bool(self.client_id and self.client_secret)

    def _token(self):
        key = f"airtel_token:{self.client_id}"
        token = cache.get(key)
        if token:
            return token
        resp = requests.post(
            f"{self.base_url}/auth/oauth2/token",
            json={"client_id": self.client_id, "client_secret": self.client_secret,
                  "grant_type": "client_credentials"},
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            raise GatewayError(f"Airtel token request failed ({resp.status_code})")
        data = resp.json()
        token = data["access_token"]
        cache.set(key, token, max(int(data.get("expires_in", 180)) - 30, 30))
        return token

    def _headers(self):
        return {
            "Authorization": f"Bearer {self._token()}",
            "X-Country": self.country,
            "X-Currency": self.currency,
            "Content-Type": "application/json",
            "Accept": "*/*",
        }

    def request_to_pay(self, *, amount, msisdn, external_id, payer_message, payee_note):
        reference = uuid.uuid4().hex[:20].upper()
        local = msisdn.lstrip("+")
        if local.startswith("250"):
            local = local[3:]
        body = {
            "reference": payer_message[:64],
            "subscriber": {"country": self.country, "currency": self.currency, "msisdn": local},
            "transaction": {"amount": int(amount), "country": self.country,
                            "currency": self.currency, "id": reference},
        }
        resp = requests.post(
            f"{self.base_url}/merchant/v1/payments/",
            json=body, headers=self._headers(), timeout=TIMEOUT,
        )
        data = {}
        try:
            data = resp.json()
        except ValueError:
            pass
        success = (data.get("status") or {}).get("success")
        if resp.status_code not in (200, 201, 202) or success is False:
            logger.warning("Airtel collection rejected: %s %s", resp.status_code, resp.text[:300])
            raise GatewayError("Airtel Money could not send the payment prompt. Check the number and try again.")
        return GatewayResult(status="pending", reference=reference, message="Payment prompt sent.", raw=data)

    def get_status(self, reference):
        resp = requests.get(
            f"{self.base_url}/standard/v1/payments/{reference}",
            headers=self._headers(), timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            raise GatewayError(f"Airtel status lookup failed ({resp.status_code})")
        data = resp.json()
        txn = (data.get("data") or {}).get("transaction") or {}
        status = self.STATUS_MAP.get((txn.get("status") or "").upper(), "pending")
        return GatewayResult(
            status=status, reference=reference,
            provider_txn_id=txn.get("airtel_money_id", "") or "",
            message=txn.get("message", "") or "", raw=data,
        )


GATEWAYS = {
    "mtn_momo": MTNMoMoGateway,
    "airtel_money": AirtelMoneyGateway,
}


def get_gateway(method):
    cls = GATEWAYS.get(method)
    return cls() if cls else None
