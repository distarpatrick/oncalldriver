"""
Extra security layers:

* SecurityHeadersMiddleware – Content-Security-Policy, Permissions-Policy and
  related headers on every response.
* LoginRateLimitMiddleware  – throttles POSTs to the sign-in page and Django
  admin login per IP + username to stop password guessing.
"""
import hashlib

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect

CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net",
    "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com",
    "img-src 'self' data: blob: https:",
    "media-src 'self' blob: https:",
    "connect-src 'self'",
    "frame-src 'self' https://www.google.com https://maps.google.com https://www.youtube.com",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "base-uri 'self'",
    "object-src 'none'",
])


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(self), payment=(self), usb=()",
        )
        response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        if request.path.startswith(("/login", "/register", "/profile", "/pay/", "/dashboard", "/" + settings.ADMIN_URL)):
            response.headers["Cache-Control"] = "no-store, private"
        return response


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class LoginRateLimitMiddleware:
    """Lock out an IP (and IP+username) after too many failed sign-ins."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.limit = getattr(settings, "LOGIN_RATE_LIMIT_ATTEMPTS", 6)
        self.window = getattr(settings, "LOGIN_RATE_LIMIT_WINDOW", 900)

    def _is_login_post(self, request):
        if request.method != "POST":
            return False
        path = request.path
        if path.startswith("/" + settings.ADMIN_URL + "login"):
            return True
        return path in ("/login/", "/register/") and request.POST.get("action") != "register"

    def _keys(self, request):
        ip = client_ip(request)
        username = (request.POST.get("username") or request.POST.get("email") or "").strip().lower()
        digest = hashlib.sha256(f"{ip}|{username}".encode()).hexdigest()[:32]
        return f"login_fail_ip:{ip}", f"login_fail_user:{digest}"

    def __call__(self, request):
        if not self._is_login_post(request):
            return self.get_response(request)

        ip_key, user_key = self._keys(request)
        if cache.get(user_key, 0) >= self.limit or cache.get(ip_key, 0) >= self.limit * 3:
            minutes = max(self.window // 60, 1)
            if request.path.startswith("/" + settings.ADMIN_URL):
                return HttpResponse(
                    f"Too many failed sign-in attempts. Try again in {minutes} minutes.",
                    status=429, content_type="text/plain",
                )
            messages.error(request, f"Too many failed sign-in attempts. Please wait {minutes} minutes and try again.")
            return redirect(request.path + "?mode=login")

        was_anonymous = not request.user.is_authenticated
        response = self.get_response(request)
        logged_in = was_anonymous and getattr(request, "user", None) is not None and request.user.is_authenticated

        if logged_in:
            cache.delete(user_key)
        else:
            for key in (ip_key, user_key):
                try:
                    cache.incr(key)
                except ValueError:
                    cache.set(key, 1, self.window)
        return response


class HealthCheckMiddleware:
    """Answer Render's health check at /healthz before host validation and the
    HTTPS redirect run, so internal probes (plain HTTP, internal Host header)
    always get a 200."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/healthz":
            return HttpResponse("ok", content_type="text/plain")
        return self.get_response(request)
