from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.forms import PasswordResetForm
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
from django.http import FileResponse
from .forms import SiteSettingsForm
from django.urls import reverse
from django.db.models import ProtectedError
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import re
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import (
    Count, Sum, Q, Avg, F
)
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import timedelta
import json

from .models import (
    Car, CarBrand, CarPhoto, CarView,
    Booking, VisitSchedule, Payment, Invoice, Refund,
    Notification, SupportTicket, TicketReply,
    AuditLog, SiteSettings, Promotion, CarReview,
    CompanyCarOwner, CustomUser, SiteMessage,
)
from homepage.forms import StaffCreationForm, CarUploadForm, CompanyCarOwnerForm
from datetime import datetime
from decimal import Decimal
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import Q, Count
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import BookingForm, CarSearchForm
from .models import (Booking,Car,CarBrand,CarPhoto,CarVideo,CarView,CarWishlist,AuditLog,Payment,SupportTicket,VisitSchedule,CarComment,CarReview,CarFeature,
    SiteSettings,
)
from .forms import (CarMediaUploadForm,CarUploadForm,CompanyCarOwnerForm,CustomerRegistrationForm,LoginForm,ProfileForm,StaffCreationForm,BookingForm,CarSearchForm,
    VisitScheduleForm,
    CarReviewForm,
    CarCommentForm,
)
from .twilio_whatsapp import twilio_whatsapp_service


FALLBACK_SLIDES = [
    {
        "image": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1800&q=85",
        "title": "Welcome to On Call Driver",
        "text": "Find inspected cars, schedule visits, and drive with confidence.",
    },
    {
        "image": "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?auto=format&fit=crop&w=1800&q=85",
        "title": "Premium Cars, Ready When You Are",
        "text": "Explore vehicles selected for comfort, safety, and everyday performance.",
    },
    {
        "image": "https://images.unsplash.com/photo-1503736334956-4c8f8e92946d?auto=format&fit=crop&w=1800&q=85",
        "title": "Book a Visit in Minutes",
        "text": "Choose the car you love and arrange a viewing with a trusted sales team.",
    },
    {
        "image": "https://images.unsplash.com/photo-1542362567-b07e54358753?auto=format&fit=crop&w=1800&q=85",
        "title": "Drive More Than a Car",
        "text": "Get a smooth buying experience from discovery to payment.",
    },
    {
        "image": "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?auto=format&fit=crop&w=1800&q=85",
        "title": "New Arrivals Every Week",
        "text": "Stay close to fresh stock from trusted owners and verified marketers.",
    },
    {
        "image": "https://images.unsplash.com/photo-1525609004556-c46c7d6cf023?auto=format&fit=crop&w=1800&q=85",
        "title": "Smart Choices for Every Journey",
        "text": "Compare fuel, transmission, mileage, and price before you visit.",
    },
    {
        "image": "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=1800&q=85",
        "title": "Transparent Pricing",
        "text": "See car prices, scheduling fees, and negotiable options clearly.",
    },
    {
        "image": "https://images.unsplash.com/photo-1541443131876-44b03de101c5?auto=format&fit=crop&w=1800&q=85",
        "title": "Support at Every Step",
        "text": "Our team helps you move from interest to ownership without stress.",
    },
    {
        "image": "https://images.unsplash.com/photo-1555353540-64580b51c258?auto=format&fit=crop&w=1800&q=85",
        "title": "Built for Rwanda's Roads",
        "text": "Discover cars listed with local location, plate, and inspection details.",
    },
    {
        "image": "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&w=1800&q=85",
        "title": "Your Next Drive Starts Here",
        "text": "On Call Driver brings cars, service, and booking into one platform.",
    },
]


def media_url(field_file):
    if not field_file:
        return ""
    try:
        if field_file.name and field_file.storage.exists(field_file.name):
            return field_file.url
    except (OSError, ValueError):
        return ""
    return ""


def get_site_context():
    site_settings = SiteSettings.objects.first()
    return {
        "site": site_settings,
        "site_name": site_settings.site_name if site_settings else "On Call Driver",
        "site_logo": media_url(site_settings.site_logo) if site_settings else "",
    }


def build_car_cards(cars_queryset):
    cars = list(cars_queryset)
    car_ids = [car.id for car in cars]
    cover_photos = {
        photo.car_id: media_url(photo.photo)
        for photo in CarPhoto.objects.filter(car_id__in=car_ids, is_cover=True)
        if media_url(photo.photo)
    }
    first_photos = {}
    for photo in CarPhoto.objects.filter(car_id__in=car_ids).order_by("order", "uploaded_at"):
        url = media_url(photo.photo)
        if url:
            first_photos.setdefault(photo.car_id, url)
    return [
        {
            "car": car,
            "image": cover_photos.get(car.id) or first_photos.get(car.id),
        }
        for car in cars
    ]


def admin_role_required(user):
    return user.is_authenticated and user.role in ("super_admin", "admin")


def dashboard_role_required(user):
    return user.is_authenticated and user.role in (
        "super_admin", "admin", "manager", "marketer",
        "sales_agent", "accountant", "inventory_manager", "customer_support",
    )


def car_upload_role_required(user):
    return user.is_authenticated and user.role in ("super_admin", "admin", "marketer")


def payment_review_role_required(user):
    return user.is_authenticated and user.role in ("super_admin", "admin", "accountant", "manager")


def redirect_for_user(user):
    if dashboard_role_required(user):
        return "homepage:dashboard"
    return "homepage:index"


def cleanup_expired_visit_schedules():
    """
    Remove visits whose scheduled time has passed while still awaiting attendance.
    Called from normal web views so stale visits disappear without a separate worker.
    """
    now = timezone.localtime()
    active_statuses = ("pending", "confirmed", "rescheduled")
    expired_ids = []

    schedules = VisitSchedule.objects.filter(status__in=active_statuses)
    for schedule in schedules.only("id", "visit_date", "visit_time"):
        scheduled_at = datetime.combine(schedule.visit_date, schedule.visit_time)
        if timezone.is_naive(scheduled_at):
            scheduled_at = timezone.make_aware(scheduled_at, timezone.get_current_timezone())
        if scheduled_at < now:
            expired_ids.append(schedule.id)

    if expired_ids:
        VisitSchedule.objects.filter(id__in=expired_ids).delete()

    return len(expired_ids)


def cleanup_expired_site_messages(days=2):
    cutoff = timezone.now() - timedelta(days=days)
    return SiteMessage.objects.filter(created_at__lt=cutoff).delete()[0]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _record_view(car, request):
    """Increment views_count once per session per car."""
    session_key = f"viewed_car_{car.pk}"
    if not request.session.get(session_key):
        ip = (
            request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR")
        )
        CarView.objects.create(
            car=car,
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip,
        )
        car.views_count += 1
        car.save(update_fields=["views_count"])
        request.session[session_key] = True


def _rating_breakdown(car):
    """Return dict {star: count} for stars 1–5."""
    qs = car.reviews.filter(is_approved=True)
    breakdown = {str(i): 0 for i in range(1, 6)}
    for row in qs.values("rating").annotate(count=Count("rating")):
        breakdown[str(row["rating"])] = row["count"]
    return breakdown


def _get_whatsapp():
    try:
        return SiteSettings.objects.get(pk=1).whatsapp_number or ""
    except SiteSettings.DoesNotExist:
        return ""


def index(request):
    cleanup_expired_visit_schedules()
    site_context = get_site_context()
    site_settings = site_context["site"]
    visible_cars = Car.objects.filter(status__in=["available", "scheduled", "booked"]).select_related("brand")
    featured_cars = list(visible_cars.filter(is_featured=True).order_by("-created_at")[:6])
    featured_car_ids = [car.id for car in featured_cars]

    cover_photos = {
        photo.car_id: media_url(photo.photo)
        for photo in CarPhoto.objects.filter(car_id__in=featured_car_ids, is_cover=True)
        if media_url(photo.photo)
    }
    first_photos = {}
    for photo in CarPhoto.objects.filter(car_id__in=featured_car_ids).order_by("order", "uploaded_at"):
        url = media_url(photo.photo)
        if url:
            first_photos.setdefault(photo.car_id, url)

    car_cards = []
    for car in featured_cars:
        car_cards.append(
            {
                "pk": car.pk,
                "title": car.title,
                "brand": car.brand.name if car.brand else "On Call Driver",
                "model": car.model,
                "year": car.year,
                "price": car.price,
                "location": f"{car.district}, {car.province}",
                "transmission": car.get_transmission_display(),
                "fuel": car.get_fuel_type_display(),
                "mileage": car.mileage_km,
                "rating": car.average_rating,
                "image": cover_photos.get(car.id) or first_photos.get(car.id),
                "status": car.get_status_display(),
                "book_url": reverse("homepage:book_car", args=[car.pk]),
                "schedule_url": reverse("homepage:schedule_visit", args=[car.pk]),
                "modal_url": reverse("homepage:car_modal_info", args=[car.pk]),
            }
        )

    database_slides = []
    if site_settings and site_settings.hero_banner:
        hero_banner_url = media_url(site_settings.hero_banner)
        if hero_banner_url:
            database_slides.append(
                {
                    "image": hero_banner_url,
                    "title": site_settings.tagline or "Welcome to On Call Driver",
                    "text": "A polished car marketplace with reliable booking, visits, and driver support.",
                }
            )

        for photo in CarPhoto.objects.select_related("car").filter(car__status__in=["available", "scheduled", "booked"])[:10]:
            photo_url = media_url(photo.photo)
            if photo_url:
                database_slides.append(
                    {
                        "image": photo_url,
                        "title": photo.caption or photo.car.title,
                        "text": f"{photo.car.year} {photo.car.model} available in {photo.car.district}.",
                    }
                )

    hero_slides = (database_slides + FALLBACK_SLIDES)[:10]
    videos = [
        video
        for video in CarVideo.objects.select_related("car").filter(car__status__in=["available", "scheduled", "booked"])
        if media_url(video.video)
    ][:2]

    context = {
        **site_context,
        "hero_slides": hero_slides,
        "featured_cars": car_cards,
        "videos": videos,
        "fallback_videos": range(max(0, 2 - len(videos))),
    }
    return render(request, "homepage/index.html", context)


def make_book_visit(request):
    cleanup_expired_visit_schedules()
    cars_queryset = (
        Car.objects.filter(status__in=["available", "scheduled"])
        .select_related("brand")
        .prefetch_related("photos")
        .order_by("-is_featured", "-created_at")
    )
    car_cards = build_car_cards(cars_queryset)

    booking_initial = {}
    visit_initial = {}
    if request.user.is_authenticated:
        booking_initial = {
            "full_name": request.user.full_name,
            "phone": request.user.phone,
            "email": request.user.email,
        }
        visit_initial = {
            "full_name": request.user.full_name,
            "phone": request.user.phone,
            "district": request.user.district or "",
        }

    context = {
        **get_site_context(),
        "car_cards": car_cards,
        "booking_form": BookingForm(initial=booking_initial),
        "visit_form": VisitScheduleForm(initial=visit_initial),
    }
    return render(request, "homepage/make_booK_visit.html", context)


def cars(request):
    cleanup_expired_visit_schedules()
    query = request.GET.get("q", "").strip()
    visible_cars = (
        Car.objects.filter(status__in=["available", "scheduled", "booked"])
        .select_related("brand", "owner", "uploaded_by")
        .order_by("-created_at")
    )

    if query:
        search_filter = (
            Q(title__icontains=query)
            | Q(brand__name__icontains=query)
            | Q(model__icontains=query)
            | Q(color__icontains=query)
            | Q(registration_plate__icontains=query)
            | Q(province__icontains=query)
            | Q(district__icontains=query)
        )
        if query.isdigit():
            search_filter |= Q(year=int(query))
        visible_cars = visible_cars.filter(search_filter)

    paginator = Paginator(visible_cars, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    car_cards = build_car_cards(page_obj.object_list)

    context = {
        **get_site_context(),
        "car_cards": car_cards,
        "page_obj": page_obj,
        "query": query,
        "total_cars": paginator.count,
    }
    return render(request, "homepage/cars_on_the_market.html", context)


def auth_view(request):
    if request.user.is_authenticated:
        return redirect(redirect_for_user(request.user))

    login_form = LoginForm(request=request)
    register_form = CustomerRegistrationForm()
    requested_mode = request.GET.get("mode")
    active_panel = "register" if requested_mode == "register" or request.resolver_match.url_name == "register" else "login"

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "register":
            active_panel = "register"
            register_form = CustomerRegistrationForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                twilio_sent = twilio_whatsapp_service.send_account_welcome(user)
                login(request, user)
                if twilio_sent:
                    messages.success(request, "Your customer account has been created. We sent you a WhatsApp welcome message.")
                else:
                    messages.success(request, "Your customer account has been created.")
                return redirect(redirect_for_user(user))
        else:
            login_form = LoginForm(request=request, data=request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)
                messages.success(request, f"Welcome back, {user.full_name}.")
                return redirect(redirect_for_user(user))

    context = {
        **get_site_context(),
        "login_form": login_form,
        "register_form": register_form,
        "active_panel": active_panel,
    }
    return render(request, "user/auth.html", context)


def password_reset_request(request):
    """Handle AJAX or form password reset requests by sending reset email."""
    if request.method != "POST":
        return JsonResponse({"success": False, "errors": {"__all__": ["Invalid request method."]}}, status=400)

    email = request.POST.get("email") or request.POST.get("username")
    if not email:
        return JsonResponse({"success": False, "errors": {"email": ["Email is required."]}}, status=400)

    form = PasswordResetForm(data={"email": email})
    if form.is_valid():
        # Uses the default templates under registration/ for the email body and subject
        form.save(request=request, use_https=request.is_secure())
        return JsonResponse({"success": True, "message": "If an account with that email exists, a reset link has been sent."})
    else:
        return JsonResponse({"success": False, "errors": form.errors}, status=400)


def logout_view(request):
    logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("homepage:auth")


@login_required
def profile(request):
    cleanup_expired_visit_schedules()
    user = request.user
    form = ProfileForm(instance=request.user)

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("homepage:profile")

    customer_stats = {
        "Bookings": user.bookings.count(),
        "Visits": user.schedules.count(),
        "Wishlist": user.wishlists.count(),
        "Payments": user.payments.count(),
    }
    staff_stats = {
        "Uploaded Cars": user.uploaded_cars.count(),
        "Handled Bookings": user.handled_bookings.count(),
        "Confirmed Visits": user.confirmed_schedules.count(),
        "Processed Payments": user.processed_payments.count(),
    }
    admin_stats = {
        "Active Users": StaffCreationForm.Meta.model.objects.filter(is_active=True).count(),
        "Cars Live": Car.objects.filter(status__in=("available", "scheduled", "booked")).count(),
        "Pending Cars": Car.objects.filter(status="pending").count(),
        "Open Tickets": SupportTicket.objects.exclude(status__in=("resolved", "closed")).count(),
    }
    support_stats = {
        "My Tickets": user.assigned_tickets.count(),
        "Open Assigned": user.assigned_tickets.exclude(status__in=("resolved", "closed")).count(),
        "Customer Tickets": SupportTicket.objects.filter(submitted_by=user).count(),
        "Replies": user.ticketreply_set.count(),
    }

    role_actions = [
        {"label": "Browse Cars", "url": "homepage:car_list", "icon": "fa-car-side"},
        {"label": "Account Security", "url": "homepage:profile_security", "icon": "fa-shield-halved"},
    ]
    if dashboard_role_required(user):
        role_actions.append({"label": "Dashboard", "url": "homepage:dashboard", "icon": "fa-chart-line"})
    if user.role in ("super_admin", "admin", "marketer"):
        role_actions.append({"label": "Upload Car", "url": "homepage:upload_car", "icon": "fa-cloud-arrow-up"})

    can_review_payments = payment_review_role_required(user)
    recent_bookings_page = _paginate(request, user.bookings.select_related("car").order_by("-created_at"), 8, "bp")
    recent_schedules_page = _paginate(request, user.schedules.select_related("car").order_by("-created_at"), 8, "sp")
    recent_payments_page = _paginate(request, user.payments.select_related("booking__car", "schedule__car").order_by("-created_at"), 8, "pp")
    recent_invoices_page = _paginate(request, user.invoices.select_related("payment__booking", "payment__schedule", "issued_by").order_by("-created_at"), 8, "ip")
    payment_work = Payment.objects.none()
    if can_review_payments:
        payment_work = (
            Payment.objects.select_related("customer", "booking__car", "schedule__car", "processed_by")
            .order_by("-created_at")[:20]
        )

    context = {
        **get_site_context(),
        "form": form,
        "profile_photo_url": media_url(user.profile_photo),
        "customer_stats": customer_stats,
        "staff_stats": staff_stats,
        "admin_stats": admin_stats,
        "support_stats": support_stats,
        "role_actions": role_actions,
        "recent_bookings": recent_bookings_page.object_list,
        "recent_bookings_page": recent_bookings_page,
        "recent_schedules": recent_schedules_page.object_list,
        "recent_schedules_page": recent_schedules_page,
        "recent_wishlist": user.wishlists.select_related("car", "car__brand").order_by("-added_at"),
        "recent_uploaded_cars": user.uploaded_cars.select_related("brand").order_by("-created_at")[:5],
        "recent_handled_bookings": user.handled_bookings.select_related("car", "customer").order_by("-created_at")[:5],
        "recent_payments": recent_payments_page.object_list,
        "recent_payments_page": recent_payments_page,
        "recent_invoices": recent_invoices_page.object_list,
        "recent_invoices_page": recent_invoices_page,
        "can_review_payments": can_review_payments,
        "payment_work": payment_work,
        "assigned_tickets": user.assigned_tickets.select_related("submitted_by").order_by("-created_at")[:5],
        "audit_logs": AuditLog.objects.filter(user=user).order_by("-timestamp")[:5],
    }
    return render(request, "user/profile.html", context)


@login_required
def profile_security(request):
    form = PasswordChangeForm(user=request.user)

    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been updated.")
            return redirect("homepage:profile")

    context = {
        **get_site_context(),
        "form": form,
        "profile_photo_url": media_url(request.user.profile_photo),
    }
    return render(request, "user/profile_security.html", context)


@login_required
@require_POST
def update_visit_schedule(request, schedule_id):
    cleanup_expired_visit_schedules()
    schedule = get_object_or_404(
        VisitSchedule,
        id=schedule_id,
        customer=request.user,
        status__in=("pending", "confirmed", "rescheduled"),
    )

    visit_date = request.POST.get("visit_date")
    visit_time = request.POST.get("visit_time")
    district = request.POST.get("district", "").strip()
    notes = request.POST.get("notes", "").strip()

    if not visit_date or not visit_time or not district:
        messages.error(request, "Visit date, time, and district are required.")
        return redirect("homepage:profile")

    try:
        scheduled_at = datetime.fromisoformat(f"{visit_date}T{visit_time}")
    except ValueError:
        messages.error(request, "Enter a valid visit date and time.")
        return redirect("homepage:profile")

    scheduled_at = timezone.make_aware(scheduled_at, timezone.get_current_timezone())
    if scheduled_at <= timezone.localtime():
        messages.error(request, "Visit date and time must be in the future.")
        return redirect("homepage:profile")

    schedule.visit_date = scheduled_at.date()
    schedule.visit_time = scheduled_at.time()
    schedule.district = district
    schedule.notes = notes
    if schedule.status == "confirmed":
        schedule.status = "rescheduled"
    schedule.save(update_fields=["visit_date", "visit_time", "district", "notes", "status", "updated_at"])
    messages.success(request, f"Visit schedule {schedule.schedule_number} has been updated.")
    return redirect("homepage:profile")


@login_required
@require_POST
def delete_visit_schedule(request, schedule_id):
    schedule = get_object_or_404(VisitSchedule, id=schedule_id, customer=request.user)
    schedule_number = schedule.schedule_number
    schedule.delete()
    messages.success(request, f"Visit schedule {schedule_number} has been deleted.")
    return redirect("homepage:profile")


@login_required
@require_POST
def delete_wishlist(request, wishlist_id):
    wishlist = get_object_or_404(CarWishlist, id=wishlist_id, user=request.user)
    title = wishlist.car.title
    wishlist.delete()
    messages.success(request, f"{title} has been removed from your wishlist.")
    return redirect("homepage:profile")


@login_required
@user_passes_test(payment_review_role_required)
@require_POST
def confirm_payment(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related("booking", "schedule"),
        id=payment_id,
    )
    payment.status = "success"
    payment.processed_by = request.user
    payment.failure_reason = ""
    payment.save(update_fields=["status", "processed_by", "failure_reason", "paid_at"])

    if payment.schedule:
        payment.schedule.fee_paid = True
        if payment.schedule.status == "pending":
            payment.schedule.status = "confirmed"
        payment.schedule.confirmed_by = request.user
        payment.schedule.save(update_fields=["fee_paid", "status", "confirmed_by", "updated_at"])

    if payment.booking and payment.booking.status == "pending":
        payment.booking.status = "confirmed"
        payment.booking.handled_by = request.user
        payment.booking.save(update_fields=["status", "handled_by", "updated_at"])

    _ensure_invoice_for_payment(payment, request.user, request=request)

    twilio_sent = twilio_whatsapp_service.send_payment_confirmation(payment, request=request)
    if not twilio_sent:
        messages.warning(request, "Payment was confirmed, but the WhatsApp confirmation could not be sent. Please check the Twilio settings and WhatsApp logs.")

    messages.success(request, f"Payment {payment.payment_number} has been confirmed.")
    return _redirect_after_payment_confirmation(payment, "homepage:profile")



@login_required
@user_passes_test(car_upload_role_required)
def upload_car(request):
    owner_form = CompanyCarOwnerForm(prefix="owner")
    car_form = CarUploadForm(prefix="car")
    media_form = CarMediaUploadForm(prefix="media")

    if request.method == "POST":
        owner_form = CompanyCarOwnerForm(request.POST, request.FILES, prefix="owner")
        car_form = CarUploadForm(request.POST, prefix="car")
        media_form = CarMediaUploadForm(request.POST, request.FILES, prefix="media")

        if owner_form.is_valid() and car_form.is_valid() and media_form.is_valid():
            with transaction.atomic():
                owner = owner_form.save(commit=False)
                owner.registered_by = request.user
                owner.save()

                car = car_form.save(commit=False)
                brand_name = car_form.cleaned_data["brand_name"].strip()
                brand, _ = CarBrand.objects.get_or_create(
                    name__iexact=brand_name,
                    defaults={"name": brand_name},
                )
                car.owner = owner
                car.brand = brand
                car.uploaded_by = request.user
                car.status = "available"
                car.save()

                for index, photo in enumerate(media_form.cleaned_data["photos"]):
                    CarPhoto.objects.create(
                        car=car,
                        photo=photo,
                        is_cover=index == 0,
                        order=index,
                    )

                for video in media_form.cleaned_data["videos"]:
                    CarVideo.objects.create(
                        car=car,
                        video=video,
                        title=video.name,
                    )

            messages.success(request, f"{car.title} has been uploaded and sent for review.")
            return redirect("homepage:upload_car")

    recent_cars = build_car_cards(
        Car.objects.select_related("brand", "owner", "uploaded_by")
        .filter(uploaded_by=request.user)
        .order_by("-created_at")[:6]
    )

    context = {
        **get_site_context(),
        "owner_form": owner_form,
        "car_form": car_form,
        "media_form": media_form,
        "recent_cars": recent_cars,
    }
    return render(request, "homepage/upload_car.html", context)


# ──────────────────────────────────────────────
# Helper: record a car view (unique per session)
# ──────────────────────────────────────────────
def _record_view(car: Car, request) -> None:
    session_key = f"viewed_car_{car.pk}"
    if not request.session.get(session_key):
        CarView.objects.create(
            car=car,
            user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        car.views_count += 1
        car.save(update_fields=["views_count"])
        request.session[session_key] = True


# ──────────────────────────────────────────────
# Car listing page  (main marketplace page)
# ──────────────────────────────────────────────
def car_list(request):
    """
    GET  — renders the full marketplace template with server-side filtering.
    All filter params come from query-string so the page is shareable/bookmarkable.
    """
    cleanup_expired_visit_schedules()
    form = CarSearchForm(request.GET or None)

    # Base queryset: only cars visible on the platform
    qs = (
        Car.objects
        .filter(status__in=("available", "scheduled", "booked"))
        .select_related("brand", "owner")
        .prefetch_related("photos")
    )

    # ── Text search ──────────────────────────────
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(brand__name__icontains=q)
            | Q(model__icontains=q)
            | Q(year__icontains=q)
        )

    # ── Brand ────────────────────────────────────
    brand_name = request.GET.get("brand", "")
    if brand_name:
        qs = qs.filter(brand__name__iexact=brand_name)

    # ── Fuel type ────────────────────────────────
    fuel = request.GET.get("fuel", "")
    if fuel:
        qs = qs.filter(fuel_type=fuel)

    # ── Transmission ─────────────────────────────
    transmission = request.GET.get("transmission", "")
    if transmission:
        qs = qs.filter(transmission=transmission)

    # ── Province ─────────────────────────────────
    province = request.GET.get("province", "")
    if province:
        qs = qs.filter(province=province)

    # ── Status checkboxes ────────────────────────
    show_available = request.GET.get("show_available", "on")
    show_scheduled = request.GET.get("show_scheduled", "on")
    statuses = []
    if show_available == "on":
        statuses.append("available")
    if show_scheduled == "on":
        statuses.append("scheduled")
    show_booked = request.GET.get("show_booked", "on")
    if show_booked == "on":
        statuses.append("booked")
    if statuses:
        qs = qs.filter(status__in=statuses)
    else:
        # Nothing selected → show nothing
        qs = qs.none()

    # ── Price range ──────────────────────────────
    price_min = request.GET.get("price_min", "")
    price_max = request.GET.get("price_max", "")
    if price_min:
        try:
            qs = qs.filter(price__gte=Decimal(price_min))
        except Exception:
            pass
    if price_max:
        try:
            qs = qs.filter(price__lte=Decimal(price_max))
        except Exception:
            pass

    # ── Drive type (multi-checkbox) ──────────────
    drive_types = request.GET.getlist("drive")
    if drive_types:
        qs = qs.filter(drive_type__in=drive_types)

    # ── Feature flags ────────────────────────────
    if request.GET.get("negotiable"):
        qs = qs.filter(is_negotiable=True)
    if request.GET.get("featured"):
        qs = qs.filter(is_featured=True)

    # ── Sorting ──────────────────────────────────
    sort = request.GET.get("sort", "newest")
    sort_map = {
        "newest":     "-created_at",
        "price_asc":  "price",
        "price_desc": "-price",
        "popular":    "-views_count",
        "rating":     "-average_rating",
    }
    qs = qs.order_by(sort_map.get(sort, "-created_at"))

    # ── Sidebar counts ───────────────────────────
    visible_qs = Car.objects.filter(status__in=("available", "scheduled", "booked"))
    cnt_available = visible_qs.filter(status="available").count()
    cnt_scheduled = visible_qs.filter(status="scheduled").count()
    total_count = qs.count()

    # ── Brand list for the dropdown ───────────────
    brand_list = (
        CarBrand.objects
        .filter(is_active=True, cars__status__in=("available", "scheduled", "booked"))
        .values_list("name", flat=True)
        .distinct()
        .order_by("name")
    )

    # ── Pagination ───────────────────────────────
    paginator = Paginator(qs, 40)  # 40 per page, matching JS ITEMS_PER_PAGE
    page_number = request.GET.get("page", 1)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    # ── Wishlist state for authenticated users ────
    wishlisted_ids = set()
    if request.user.is_authenticated:
        wishlisted_ids = set(
            CarWishlist.objects
            .filter(user=request.user, car__in=page_obj.object_list)
            .values_list("car_id", flat=True)
        )

    # Attach cover photo + wishlist flag to each car for template convenience
    cars_with_meta = []
    for car in page_obj.object_list:
        cover = car.photos.filter(is_cover=True).first() or car.photos.first()
        cover_photo_url = media_url(cover.photo) if cover else ""
        cars_with_meta.append({
            "car": car,
            "cover_photo": cover,
            "cover_photo_url": cover_photo_url,
            "is_wishlisted": car.pk in wishlisted_ids,
        })

    # Showing range text
    start_idx = page_obj.start_index()
    end_idx = page_obj.end_index()

    context = {
        "form": form,
        "page_obj": page_obj,
        "cars_with_meta": cars_with_meta,
        "total_count": total_count,
        "cnt_available": cnt_available,
        "cnt_scheduled": cnt_scheduled,
        "brand_list": brand_list,
        "showing_range": f"{start_idx}–{end_idx}" if total_count else "0–0",
        "showing_total": total_count,
        # Pass current GET params back for filter persistence
        "current_q": q,
        "current_brand": brand_name,
        "current_fuel": fuel,
        "current_transmission": transmission,
        "current_province": province,
        "current_sort": sort,
        "current_price_min": price_min,
        "current_price_max": price_max,
        "current_drive": drive_types,
        "show_available": show_available,
        "show_scheduled": show_scheduled,
        "show_booked": show_booked,
        "negotiable_checked": request.GET.get("negotiable", ""),
        "featured_checked": request.GET.get("featured", ""),
    }
    return render(request, "homepage/cars_on_the_market.html", context)


def _search_result_actions_for_user(user, item_type, obj):
    actions = []
    if item_type == "car":
        actions.append({"label": "View car", "url": reverse("homepage:car_detail", args=[obj.pk])})
    elif item_type == "booking":
        actions.append({"label": "View booking", "url": reverse("homepage:booking_detail", args=[obj.pk])})
        actions.append({"label": "Open car", "url": reverse("homepage:car_detail", args=[obj.car.pk])})
    elif item_type == "schedule":
        actions.append({"label": "View visit", "url": reverse("homepage:schedule_detail", args=[obj.pk])})
        actions.append({"label": "Open car", "url": reverse("homepage:car_detail", args=[obj.car.pk])})
    elif item_type == "invoice":
        actions.append({"label": "Open invoice", "url": reverse("homepage:download_invoice", args=[obj.pk])})
        actions.append({"label": "Open account", "url": reverse("homepage:dashboard") + "#customer-accounts"})
    elif item_type == "customer":
        actions.append({"label": "Open dashboard", "url": reverse("homepage:dashboard") + "#customer-accounts"})
    return actions


def _build_search_payload(request, query):
    normalized_query = query.strip()
    if len(normalized_query) < 1:
        return {"groups": [], "total": 0}

    is_staff_search = request.user.is_authenticated and dashboard_role_required(request.user)
    groups = []
    total = 0

    car_filters = (
        Q(title__icontains=normalized_query)
        | Q(model__icontains=normalized_query)
        | Q(brand__name__icontains=normalized_query)
        | Q(registration_plate__icontains=normalized_query)
        | Q(stock_number__icontains=normalized_query)
        | Q(district__icontains=normalized_query)
        | Q(province__icontains=normalized_query)
    )
    car_qs = Car.objects.select_related("brand", "owner", "uploaded_by").prefetch_related("photos")
    if not is_staff_search:
        car_qs = car_qs.filter(status__in=("available", "scheduled", "booked"))
    car_qs = car_qs.filter(car_filters).order_by("-created_at")[:6]
    car_items = []
    for car in car_qs:
        photo = car.photos.filter(is_cover=True).first() or car.photos.first()
        car_items.append(
            {
                "type": "car",
                "title": car.title,
                "subtitle": " • ".join(
                    filter(
                        None,
                        [
                            car.registration_plate or "",
                            car.brand.name if car.brand else "",
                            f"{car.district}, {car.province}" if car.district or car.province else "",
                        ],
                    )
                ),
                "badge": car.get_status_display(),
                "image": media_url(photo.photo) if photo else "",
                "url": reverse("homepage:car_detail", args=[car.pk]),
                "actions": _search_result_actions_for_user(request.user, "car", car),
            }
        )
    if car_items:
        groups.append({"label": "Cars", "items": car_items})
        total += len(car_items)

    if is_staff_search:
        customer_qs = (
            CustomUser.objects.filter(
                Q(role="customer")
                & (
                    Q(full_name__icontains=normalized_query)
                    | Q(email__icontains=normalized_query)
                    | Q(phone__icontains=normalized_query)
                    | Q(district__icontains=normalized_query)
                    | Q(province__icontains=normalized_query)
                )
            )
            .order_by("-date_joined")[:6]
        )
        customer_items = []
        for customer in customer_qs:
            customer_items.append(
                {
                    "type": "customer",
                    "title": customer.full_name,
                    "subtitle": " • ".join(filter(None, [customer.email, customer.phone, customer.get_role_display()])),
                    "badge": "Customer",
                    "image": media_url(customer.profile_photo) if customer.profile_photo else "",
                    "url": reverse("homepage:dashboard") + "#customer-accounts",
                    "actions": _search_result_actions_for_user(request.user, "customer", customer),
                }
            )
        if customer_items:
            groups.append({"label": "Customers", "items": customer_items})
            total += len(customer_items)

        booking_qs = (
            Booking.objects.select_related("car", "customer")
            .filter(
                Q(booking_number__icontains=normalized_query)
                | Q(car__title__icontains=normalized_query)
                | Q(car__registration_plate__icontains=normalized_query)
                | Q(customer__full_name__icontains=normalized_query)
                | Q(customer__email__icontains=normalized_query)
                | Q(customer__phone__icontains=normalized_query)
            )
            .order_by("-created_at")[:6]
        )
        booking_items = []
        for booking in booking_qs:
            booking_items.append(
                {
                    "type": "booking",
                    "title": booking.booking_number,
                    "subtitle": " • ".join(
                        filter(
                            None,
                            [
                                booking.customer.full_name,
                                booking.car.title,
                                booking.get_status_display(),
                            ],
                        )
                    ),
                    "badge": "Booking",
                    "image": "",
                    "url": reverse("homepage:booking_detail", args=[booking.pk]),
                    "actions": _search_result_actions_for_user(request.user, "booking", booking),
                }
            )
        if booking_items:
            groups.append({"label": "Bookings", "items": booking_items})
            total += len(booking_items)

        schedule_qs = (
            VisitSchedule.objects.select_related("car", "customer")
            .filter(
                Q(schedule_number__icontains=normalized_query)
                | Q(car__title__icontains=normalized_query)
                | Q(car__registration_plate__icontains=normalized_query)
                | Q(customer__full_name__icontains=normalized_query)
                | Q(customer__email__icontains=normalized_query)
                | Q(customer__phone__icontains=normalized_query)
                | Q(district__icontains=normalized_query)
            )
            .order_by("-created_at")[:6]
        )
        schedule_items = []
        for schedule in schedule_qs:
            schedule_items.append(
                {
                    "type": "schedule",
                    "title": schedule.schedule_number,
                    "subtitle": " • ".join(
                        filter(
                            None,
                            [
                                schedule.customer.full_name,
                                schedule.car.title,
                                schedule.district,
                                schedule.get_status_display(),
                            ],
                        )
                    ),
                    "badge": "Visit",
                    "image": "",
                    "url": reverse("homepage:schedule_detail", args=[schedule.pk]),
                    "actions": _search_result_actions_for_user(request.user, "schedule", schedule),
                }
            )
        if schedule_items:
            groups.append({"label": "Visits", "items": schedule_items})
            total += len(schedule_items)

        invoice_qs = (
            Invoice.objects.select_related("payment", "issued_to")
            .filter(
                Q(invoice_number__icontains=normalized_query)
                | Q(payment__payment_number__icontains=normalized_query)
                | Q(issued_to__full_name__icontains=normalized_query)
                | Q(issued_to__email__icontains=normalized_query)
                | Q(issued_to__phone__icontains=normalized_query)
            )
            .order_by("-created_at")[:6]
        )
        invoice_items = []
        for invoice in invoice_qs:
            invoice_items.append(
                {
                    "type": "invoice",
                    "title": invoice.invoice_number,
                    "subtitle": " • ".join(
                        filter(
                            None,
                            [
                                invoice.issued_to.full_name,
                                invoice.payment.payment_number,
                                f"{invoice.payment.amount:,.0f} RWF",
                            ],
                        )
                    ),
                    "badge": "Invoice",
                    "image": "",
                    "url": reverse("homepage:download_invoice", args=[invoice.pk]),
                    "actions": _search_result_actions_for_user(request.user, "invoice", invoice),
                }
            )
        if invoice_items:
            groups.append({"label": "Invoices", "items": invoice_items})
            total += len(invoice_items)

    return {"groups": groups, "total": total}


def global_search(request):
    query = request.GET.get("q", "").strip()
    payload = _build_search_payload(request, query)
    payload["query"] = query
    payload["scope"] = "dashboard" if request.user.is_authenticated and dashboard_role_required(request.user) else "public"
    return JsonResponse(payload)


# ──────────────────────────────────────────────
# Car detail page
# ──────────────────────────────────────────────
def car_detail(request, pk):
    """
    Main public car detail page.
    Handles GET only; booking/scheduling/reviews/comments have dedicated views.
    """
    car = get_object_or_404(
        Car.objects.select_related(
            "brand", "owner", "uploaded_by", "approved_by"
        ).prefetch_related(
            "photos", "videos", "features",
            "reviews__customer",
            "comments__user", "comments__replies__user",
        ),
        pk=pk,
    )

    # Only visible cars are public; admins/staff can preview all
    if not car.is_visible_on_platform():
        if not (request.user.is_authenticated and request.user.is_staff):
            messages.error(request, "This listing is no longer available.")
            return redirect("homepage:car_list")

    _record_view(car, request)

    reviews   = car.reviews.filter(is_approved=True).select_related("customer")
    comments  = (
        car.comments
        .filter(is_approved=True, parent__isnull=True)
        .prefetch_related("replies__user")
        .select_related("user")
    )
    features_summary_list = [
        feature.strip()
        for feature in (car.features_summary or "").split(",")
        if feature.strip()
    ]
    ratings_breakdown = _rating_breakdown(car)
    rating_breakdown_rows = [
        {"star": star, "count": ratings_breakdown.get(str(star), 0)}
        for star in range(5, 0, -1)
    ]

    user_reviewed = False
    in_wishlist   = False
    if request.user.is_authenticated:
        user_reviewed = car.reviews.filter(customer=request.user).exists()
        in_wishlist   = CarWishlist.objects.filter(user=request.user, car=car).exists()

    context = {
        **get_site_context(),
        "car":              car,
        "reviews":          reviews,
        "comments":         comments,
        "features_summary_list": features_summary_list,
        "ratings_breakdown": ratings_breakdown,
        "rating_breakdown_rows": rating_breakdown_rows,
        "user_reviewed":    user_reviewed,
        "in_wishlist":      in_wishlist,
        "whatsapp_number":  _get_whatsapp(),
    }
    return render(request, "homepage/car_detail.html", context)


# ─────────────────────────────────────────────────────────────────────────────
# WISHLIST TOGGLE (AJAX)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def toggle_wishlist(request, pk):
    car = get_object_or_404(Car, pk=pk)
    obj, created = CarWishlist.objects.get_or_create(user=request.user, car=car)
    if not created:
        obj.delete()
        in_wishlist = False
    else:
        in_wishlist = True

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"in_wishlist": in_wishlist})

    # Fallback for non-AJAX
    msg = "Added to wishlist." if in_wishlist else "Removed from wishlist."
    messages.success(request, msg)
    return redirect("homepage:car_detail", pk=pk)


# ─────────────────────────────────────────────────────────────────────────────
# CAR REVIEW
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def car_review(request, pk):
    car = get_object_or_404(Car, pk=pk)

    if not request.user.is_customer:
        messages.error(request, "Only customers can leave reviews.")
        return redirect("homepage:car_detail", pk=pk)

    if CarReview.objects.filter(car=car, customer=request.user).exists():
        messages.error(request, "You have already reviewed this car.")
        return redirect("homepage:car_detail", pk=pk)

    form = CarReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.car      = car
        review.customer = request.user
        review.save()          # triggers car.update_rating()
        messages.success(request, "Thank you — your review has been submitted!")
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)

    return redirect("homepage:car_detail", pk=pk)


# ─────────────────────────────────────────────────────────────────────────────
# CAR COMMENT
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def car_comment(request, pk):
    car = get_object_or_404(Car, pk=pk)

    content   = request.POST.get("content", "").strip()
    parent_id = request.POST.get("parent_id")
    parent    = None

    if parent_id:
        parent = get_object_or_404(CarComment, pk=parent_id, car=car)

    if not content:
        messages.error(request, "Comment cannot be empty.")
        return redirect("homepage:car_detail", pk=pk)

    CarComment.objects.create(
        car     = car,
        user    = request.user,
        parent  = parent,
        content = content,
    )
    messages.success(request, "Your comment has been posted.")
    return redirect("homepage:car_detail", pk=pk)


# ─────────────────────────────────────────────────────────────────────────────
# BOOKING
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def car_booking(request, pk):
    """
    Show booking form (GET) and create a Booking + Payment record (POST).
    Car is hidden from the platform once the booking is confirmed.
    """
    car = get_object_or_404(Car, pk=pk)

    if car.status not in ("available", "scheduled"):
        messages.error(request, "This car is no longer available for booking.")
        return redirect("homepage:car_detail", pk=pk)

    form = BookingForm(request.POST or None, initial={
        "full_name": request.user.full_name,
        "phone":     request.user.phone,
        "email":     request.user.email,
    })

    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data

        payment_type = cd["payment_type"]
        total_price  = car.price
        amount_paid  = total_price if payment_type == "full" else total_price / 2

        # Create Booking
        booking = Booking.objects.create(
            car             = car,
            customer        = request.user,
            payment_type    = payment_type,
            total_price     = total_price,
            amount_paid     = amount_paid,
            remaining_balance = total_price - amount_paid,
            driver_needed   = cd.get("driver_needed", False),
            notes           = cd.get("notes", ""),
            status          = "confirmed",        # triggers car.mark_as_booked()
        )

        # Create Payment record
        Payment.objects.create(
            booking        = booking,
            customer       = request.user,
            amount         = amount_paid,
            payment_method = cd["payment_method"],
            purpose        = "full_payment" if payment_type == "full" else "half_payment",
            phone_number   = cd["phone"],
            status         = "pending",           # awaits accountant confirmation
        )

        messages.success(
            request,
            f"Booking {booking.booking_number} confirmed! "
            f"RWF {amount_paid:,.0f} payment is pending verification."
        )
        return redirect("homepage:booking_detail", pk=booking.pk)

    context = {
        "car":  car,
        "form": form,
    }
    return render(request, "homepage/booking_detail.html", context)


# ─────────────────────────────────────────────────────────────────────────────
# VISIT SCHEDULE
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def car_schedule(request, pk):
    """
    Show visit scheduling form (GET) and create a VisitSchedule record (POST).
    Multiple customers may schedule visits to the same car simultaneously.
    """
    car = get_object_or_404(Car, pk=pk)

    if car.status not in ("available", "scheduled"):
        messages.error(request, "This car is not available for visit scheduling.")
        return redirect("homepage:car_detail", pk=pk)

    form = VisitScheduleForm(request.POST or None, initial={
        "full_name": request.user.full_name,
        "phone":     request.user.phone,
    })

    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data

        schedule = VisitSchedule.objects.create(
            car           = car,
            customer      = request.user,
            visit_date    = cd["visit_date"],
            visit_time    = cd["visit_time"],
            district      = cd["district"],
            location      = f"{cd['district']}, Rwanda",
            scheduling_fee = car.scheduling_fee,
            fee_paid      = False,
            notes         = cd.get("notes", ""),
            status        = "pending",
        )

        # Create scheduling-fee Payment record if fee > 0
        if car.scheduling_fee > 0:
            Payment.objects.create(
                schedule       = schedule,
                customer       = request.user,
                amount         = car.scheduling_fee,
                payment_method = cd["fee_payment_method"],
                purpose        = "scheduling_fee",
                phone_number   = cd["phone"],
                status         = "pending",
            )

        messages.success(
            request,
            f"Visit {schedule.schedule_number} scheduled for "
            f"{schedule.visit_date.strftime('%d %B %Y')} at "
            f"{schedule.visit_time.strftime('%H:%M')}. "
            "We will confirm your appointment shortly."
        )
        return redirect("homepage:schedule_detail", pk=schedule.pk)

    context = {
        "car":  car,
        "form": form,
    }
    return render(request, "homepage/schedule_form.html", context)


# ─────────────────────────────────────────────────────────────────────────────
# BOOKING DETAIL (confirmation page)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def booking_detail(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("car", "customer", "handled_by"),
        pk=pk,
    )
    if not (dashboard_role_required(request.user) or booking.customer_id == request.user.id):
        messages.error(request, "You do not have permission to view that booking.")
        return redirect("homepage:profile")

    payments = booking.payments.select_related("processed_by", "invoice").order_by("-created_at")
    context = {
        **get_site_context(),
        "booking": booking,
        "payments": payments,
        "is_staff_view": dashboard_role_required(request.user),
    }
    return render(request, "homepage/booking_detail.html", context)


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULE DETAIL (confirmation page)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def schedule_detail(request, pk):
    schedule = get_object_or_404(
        VisitSchedule.objects.select_related("car", "customer", "confirmed_by"),
        pk=pk,
    )
    if not (dashboard_role_required(request.user) or schedule.customer_id == request.user.id):
        messages.error(request, "You do not have permission to view that visit schedule.")
        return redirect("homepage:profile")

    payments = schedule.payments.select_related("processed_by", "invoice").order_by("-created_at")
    context = {
        **get_site_context(),
        "schedule": schedule,
        "payments": payments,
        "is_staff_view": dashboard_role_required(request.user),
    }
    return render(request, "homepage/schedule_detail.html", context)


# ──────────────────────────────────────────────
# Book a car  (AJAX-capable)
# ──────────────────────────────────────────────
@require_POST
def book_car(request, pk):
    """
    POST — create a Booking record and hide the car from the platform.
    Works for both authenticated and guest users.
    For authenticated users, links the booking to the account.
    For guests, stores name/phone in the notes field.
    Returns JSON when the request is AJAX, redirects otherwise.
    """
    car = get_object_or_404(Car, pk=pk, status__in=("available", "scheduled"))
    form = BookingForm(request.POST, request.FILES)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if not form.is_valid():
        if is_ajax:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
        messages.error(request, "Please fix the errors in the booking form.")
        return redirect("homepage:car_detail", pk=pk)

    cd = form.cleaned_data
    payment_type = cd["payment_type"]
    total_price = car.price
    amount_paid = total_price if payment_type == "full" else total_price * Decimal("0.5")
    remaining = total_price - amount_paid

    with transaction.atomic():
        # Resolve customer
        customer = request.user if request.user.is_authenticated else None

        # If guest, we still need a user for FK — use a placeholder approach:
        # In production, you'd create a guest user or require login.
        # Here we require login for booking; guests are prompted to sign in.
        if customer is None:
            if is_ajax:
                return JsonResponse(
                    {"success": False, "errors": {"__all__": ["Please sign in to book a car."]}},
                    status=403,
                )
            messages.warning(request, "Please sign in to book a car.")
            return redirect("accounts:login")

        # Create the booking
        booking = Booking.objects.create(
            car=car,
            customer=customer,
            payment_type=payment_type,
            total_price=total_price,
            amount_paid=amount_paid,
            remaining_balance=remaining,
            driver_needed=cd.get("driver_needed", False),
            notes=(
                f"Name: {cd['full_name']} | Phone: {cd['phone']} | Email: {cd.get('email', 'N/A')}\n"
                f"{cd.get('notes', '')}"
            ).strip(),
            status="pending",   # payment waiting verification
        )

        # Record the payment
        Payment.objects.create(
            booking=booking,
            customer=customer,
            amount=amount_paid,
            payment_method=cd["payment_method"],
            purpose="full_payment" if payment_type == "full" else "half_payment",
            phone_number=cd["phone"],
            receipt_image=request.FILES.get('payment_receipt'),
            status="pending",   # accountant will verify and mark as success
        )

    if is_ajax:
        return JsonResponse({
            "success": True,
            "message": f"Booking submitted! Booking #{booking.booking_number} is pending payment verification.",
            "booking_number": booking.booking_number,
            "detail_url": reverse("homepage:booking_detail", args=[booking.pk]),
        })

    messages.success(
        request,
        f"🎉 Booking submitted! Your booking number is {booking.booking_number}. "
        f"Please upload your payment screenshot and wait for staff verification.",
    )
    return redirect("homepage:booking_detail", pk=booking.pk)


# ──────────────────────────────────────────────
# Schedule a visit  (AJAX-capable)
# ──────────────────────────────────────────────
@require_POST
def schedule_visit(request, pk):
    """
    POST — create a VisitSchedule record.
    Car stays visible (status stays 'scheduled' or 'available').
    Multiple customers can schedule the same car simultaneously.
    """
    car = get_object_or_404(Car, pk=pk, status__in=("available", "scheduled"))
    form = VisitScheduleForm(request.POST)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if not form.is_valid():
        if is_ajax:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
        messages.error(request, "Please fix the errors in the schedule form.")
        return redirect("homepage:car_detail", pk=pk)

    cd = form.cleaned_data

    if request.user is None or not request.user.is_authenticated:
        if is_ajax:
            return JsonResponse(
                {"success": False, "errors": {"__all__": ["Please sign in to schedule a visit."]}},
                status=403,
            )
        messages.warning(request, "Please sign in to schedule a visit.")
        return redirect("homepage:login")

    with transaction.atomic():
        schedule = VisitSchedule.objects.create(
            car=car,
            customer=request.user,
            visit_date=cd["visit_date"],
            visit_time=cd["visit_time"],
            district=cd["district"],
            location=car.exact_location or f"{car.district}, {car.province}",
            scheduling_fee=car.scheduling_fee,
            fee_paid=False,   # payment confirmation handled separately by accountant
            notes=(
                f"Name: {cd['full_name']} | Phone: {cd['phone']}\n"
                f"Payment method: {cd['fee_payment_method']}\n"
                f"{cd.get('notes', '')}"
            ).strip(),
            status="pending",
        )

        # Record scheduling fee payment intent
        if car.scheduling_fee > 0:
            Payment.objects.create(
                schedule=schedule,
                customer=request.user,
                amount=car.scheduling_fee,
                payment_method=cd["fee_payment_method"],
                purpose="scheduling_fee",
                phone_number=cd["phone"],
                status="pending",
            )

    if is_ajax:
        return JsonResponse({
            "success": True,
            "message": (
                f"Visit scheduled for {cd['visit_date']} at {cd['visit_time']}! "
                f"Reference: {schedule.schedule_number}"
            ),
            "schedule_number": schedule.schedule_number,
            "detail_url": reverse("homepage:schedule_detail", args=[schedule.pk]),
        })

    messages.success(
        request,
        f"📅 Visit scheduled! Reference: {schedule.schedule_number}. "
        f"We'll confirm your appointment shortly.",
    )
    return redirect("homepage:schedule_detail", pk=schedule.pk)


# ──────────────────────────────────────────────
# Toggle wishlist  (AJAX only)
# ──────────────────────────────────────────────
@login_required
@require_POST
def toggle_wishlist(request, pk):
    """
    AJAX POST — add or remove a car from the authenticated user's wishlist.
    Returns JSON with the new wishlist state.
    """
    car = get_object_or_404(Car, pk=pk)
    wishlist_entry, created = CarWishlist.objects.get_or_create(
        user=request.user, car=car
    )
    if not created:
        # Already wishlisted — remove it
        wishlist_entry.delete()
        return JsonResponse({"wishlisted": False, "message": "Removed from wishlist."})

    return JsonResponse({"wishlisted": True, "message": "Added to wishlist ❤"})


# ──────────────────────────────────────────────
# AJAX: Get car modal info (price, fee, etc.)
# ──────────────────────────────────────────────
def car_modal_info(request, pk):
    """
    AJAX GET — returns lightweight car info for populating modals without a page reload.
    """
    car = get_object_or_404(
        Car.objects.select_related("brand").prefetch_related("photos"),
        pk=pk,
        status__in=("available", "scheduled", "booked"),
    )
    cover = car.photos.filter(is_cover=True).first() or car.photos.first()
    data = {
        "id": str(car.pk),
        "title": car.title,
        "brand": car.brand.name if car.brand else "",
        "year": car.year,
        "transmission": car.transmission,
        "fuel_type": car.fuel_type,
        "province": car.province,
        "district": car.district,
        "price": str(car.price),
        "half_price": str(car.price * Decimal("0.5")),
        "scheduling_fee": str(car.scheduling_fee),
        "is_negotiable": car.is_negotiable,
        "cover_photo_url": media_url(cover.photo) if cover else "",
        "status": car.status,
    }
    return JsonResponse(data)





User = get_user_model()


# ─────────────────────────────────────────────────────────────
# ROLE GUARDS
# ─────────────────────────────────────────────────────────────

ADMIN_ROLES        = ("super_admin", "admin")
MANAGER_ROLES      = ("super_admin", "admin", "manager")
FINANCE_ROLES      = ("super_admin", "admin", "accountant", "manager")
SALES_ROLES        = ("super_admin", "admin", "sales_agent", "manager")
UPLOAD_ROLES       = ("super_admin", "admin", "marketer")
INVENTORY_ROLES    = ("super_admin", "admin", "inventory_manager")
SUPPORT_ROLES      = ("super_admin", "admin", "customer_support")
DASHBOARD_ROLES    = ("super_admin", "admin", "manager", "marketer",
                      "sales_agent", "accountant", "inventory_manager", "customer_support")


def _require_roles(*roles):
    """Decorator factory: redirect non-matching roles."""
    def decorator(view_fn):
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.role not in roles and request.user.role not in ADMIN_ROLES:
                messages.error(request, "You don't have permission to access that page.")
                return redirect("homepage:dashboard")
            return view_fn(request, *args, **kwargs)
        return wrapped
    return decorator


# ─────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────

def _now():
    return timezone.now()


def _today():
    return timezone.now().date()


def _this_month_range():
    now = _now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now


def _build_car_image(car):
    """Return cover photo URL for a car."""
    photo = car.photos.filter(is_cover=True).first() or car.photos.first()
    if photo:
        try:
            return photo.photo.url
        except Exception:
            return ""
    return ""


def _format_rwf(amount):
    if amount is None:
        return "0 RWF"
    return f"{int(amount):,} RWF"


def _paginate(request, queryset_or_list, per_page, param):
    paginator = Paginator(queryset_or_list, per_page)
    return paginator.get_page(request.GET.get(param))


def _build_absolute_url(request, path):
    if request is not None:
        return request.build_absolute_uri(path)
    base_url = getattr(settings, "SITE_BASE_URL", "").rstrip("/")
    if base_url:
        return f"{base_url}{path}"
    return path


def _ensure_invoice_for_payment(payment, issued_by, request=None):
    if payment.status != "success":
        return None
    invoice, created = Invoice.objects.get_or_create(
        payment=payment,
        defaults={
            "issued_to": payment.customer,
            "issued_by": issued_by,
        },
    )
    if invoice.issued_by_id != getattr(issued_by, "id", None):
        invoice.issued_by = issued_by
        invoice.save(update_fields=["issued_by"])

    if created:
        invoice_link = _build_absolute_url(request, reverse("homepage:download_invoice", args=[invoice.pk]))
        Notification.objects.create(
            user=payment.customer,
            title=f"Invoice {invoice.invoice_number} is ready",
            message=f"Your invoice for payment {payment.payment_number} has been generated.",
            notif_type="payment",
            link=invoice_link,
        )
    return invoice


def _can_access_invoice(user, invoice):
    if not user.is_authenticated:
        return False
    if dashboard_role_required(user):
        return True
    return invoice.issued_to_id == user.id


def _redirect_after_payment_confirmation(payment, fallback):
    if payment.booking_id:
        return redirect("homepage:booking_detail", pk=payment.booking_id)
    if payment.schedule_id:
        return redirect("homepage:schedule_detail", pk=payment.schedule_id)
    return redirect(fallback)


def _send_site_message_reply(site_message, reply_text, replied_by):
    subject = f"Re: {site_message.subject}"
    body = (
        f"Hello {site_message.name},\n\n"
        f"{reply_text}\n\n"
        "Original message:\n"
        f"{site_message.message}\n\n"
        "Best regards,\n"
        f"{replied_by.full_name}"
    )
    return send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[site_message.email],
        fail_silently=True,
    )


# ─────────────────────────────────────────────────────────────
# MAIN DASHBOARD ROUTER
# ─────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """
    Route each role to its own context builder,
    then render the single dashboard.html template.
    """
    user = request.user
    role = user.role

    # Customers go to the public site
    if role == "customer":
        return redirect("homepage:index")

    # Staff with no dashboard access
    if role not in DASHBOARD_ROLES:
        messages.error(request, "You do not have a dashboard.")
        return redirect("homepage:index")

    # Build context per role
    builders = {
        "super_admin":       _ctx_admin,
        "admin":             _ctx_admin,
        "manager":           _ctx_manager,
        "marketer":          _ctx_marketer,
        "sales_agent":       _ctx_sales,
        "accountant":        _ctx_accountant,
        "inventory_manager": _ctx_inventory,
        "customer_support":  _ctx_support,
    }
    ctx_builder = builders.get(role, _ctx_admin)
    context = ctx_builder(request)
    context["dashboard_role"] = role
    context["user"] = user
    context["site_name"] = _get_site_name()
    context["site_logo"] = _get_site_logo()
    context["unread_notifications"] = Notification.objects.filter(
        user=user, is_read=False
    ).count()
    return render(request, "homepage/dashboard.html", context)


def _get_site_name():
    s = SiteSettings.objects.first()
    return s.site_name if s else "On Call Driver"


def _get_site_logo():
    s = SiteSettings.objects.first()
    if s and s.site_logo:
        try:
            return s.site_logo.url
        except Exception:
            return ""
    return ""


# ─────────────────────────────────────────────────────────────
# ADMIN / SUPER_ADMIN CONTEXT
# ─────────────────────────────────────────────────────────────

def _ctx_admin(request):
    month_start, now = _this_month_range()
    cleanup_expired_site_messages()

    # KPI counts
    total_users      = User.objects.count()
    active_users     = User.objects.filter(is_active=True).count()
    total_cars       = Car.objects.count()
    live_cars        = Car.objects.filter(status__in=("available", "scheduled", "booked")).count()
    booked_cars      = Car.objects.filter(status="booked").count()
    sold_cars        = Car.objects.filter(status="sold").count()
    pending_cars     = Car.objects.filter(status="pending").count()
    total_bookings   = Booking.objects.count()
    month_bookings   = Booking.objects.filter(created_at__gte=month_start).count()
    open_tickets     = SupportTicket.objects.filter(status__in=("open", "in_progress")).count()
    pending_payments = Payment.objects.filter(status="pending").count()

    # Revenue this month
    month_revenue = Payment.objects.filter(
        status="success", paid_at__gte=month_start
    ).aggregate(total=Sum("amount"))["total"] or 0

    # Staff list
    staff_qs = User.objects.exclude(role__in=("customer",)).order_by("role", "full_name")
    staff_page = _paginate(request, staff_qs, 10, "staff_page")

    # Customer accounts
    customer_qs = User.objects.filter(role="customer").order_by("-date_joined")
    customer_page = _paginate(request, customer_qs, 10, "customer_page")

    # Staff creation form
    staff_form = StaffCreationForm()
    if request.method == "POST" and "create_staff" in request.POST:
        staff_form = StaffCreationForm(request.POST)
        if staff_form.is_valid():
            u = staff_form.save()
            AuditLog.objects.create(
                user=request.user, action="created",
                model_affected="CustomUser", object_id=str(u.id),
                description=f"Created staff account {u.email} with role {u.role}",
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            messages.success(request, f"{u.full_name} ({u.get_role_display()}) created successfully.")
            return redirect("homepage:dashboard")

    # Recent cars with images
    recent_cars = _cars_with_images(
        Car.objects.select_related("brand", "uploaded_by").order_by("-created_at")[:10]
    )
    booked_car_list = _cars_with_images(
        Car.objects.select_related("brand").filter(status="booked").order_by("-updated_at")[:8]
    )
    pending_car_list = _cars_with_images(
        Car.objects.select_related("brand").filter(status="pending").order_by("-created_at")[:8]
    )

    # Recent payments
    recent_payments = Payment.objects.select_related(
        "customer", "booking__car", "schedule__car", "processed_by"
    ).order_by("-created_at")[:15]

    recent_messages_qs = SiteMessage.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=2)
    ).order_by("-created_at")
    recent_messages_page = _paginate(request, recent_messages_qs, 6, "msg_page")

    # Audit logs
    audit_logs = AuditLog.objects.select_related("user").order_by("-timestamp")[:20]

    # Monthly revenue chart data (last 6 months)
    chart_data = _monthly_revenue_chart(6)

    # Booking funnel
    booking_funnel = {
        "confirmed":  Booking.objects.filter(status="confirmed").count(),
        "pending":    Booking.objects.filter(status="pending").count(),
        "completed":  Booking.objects.filter(status="completed").count(),
        "cancelled":  Booking.objects.filter(status="cancelled").count(),
    }

    # Refunds pending
    pending_refunds = Refund.objects.filter(status="pending").select_related(
        "payment__customer", "requested_by"
    )[:10]

    return {
        "view": "admin",
        # KPIs
        "total_users": total_users,
        "active_users": active_users,
        "total_cars": total_cars,
        "live_cars": live_cars,
        "booked_cars_count": booked_cars,
        "sold_cars": sold_cars,
        "pending_cars": pending_cars,
        "total_bookings": total_bookings,
        "month_bookings": month_bookings,
        "open_tickets": open_tickets,
        "pending_payments": pending_payments,
        "month_revenue": month_revenue,
        "month_revenue_fmt": _format_rwf(month_revenue),
        # Lists
        "staff": staff_page.object_list,
        "staff_page": staff_page,
        "staff_count": staff_qs.count(),
        "staff_form": staff_form,
        "staff_roles": StaffCreationForm.STAFF_ROLE_CHOICES,
        "customer_accounts": customer_page.object_list,
        "customer_page": customer_page,
        "customer_count": customer_qs.count(),
        "recent_cars": recent_cars,
        "booked_car_list": booked_car_list,
        "pending_car_list": pending_car_list,
        "recent_payments": recent_payments,
        "pending_refunds": pending_refunds,
        "audit_logs": audit_logs,
        "recent_messages_page": recent_messages_page,
        "recent_messages": recent_messages_page.object_list,
        # Charts
        "chart_data_json": json.dumps(chart_data),
        "booking_funnel": booking_funnel,
        # Flags
        "can_manage_staff": True,
        "can_manage_customers": True,
        "can_delete_listing": True,
        "can_reply_messages": True,
    }


# ─────────────────────────────────────────────────────────────
# MANAGER CONTEXT
# ─────────────────────────────────────────────────────────────

def _ctx_manager(request):
    month_start, now = _this_month_range()
    cleanup_expired_site_messages()

    # Sales report
    month_revenue = Payment.objects.filter(
        status="success", paid_at__gte=month_start
    ).aggregate(total=Sum("amount"))["total"] or 0

    # Marketer performance (cars uploaded per marketer this month)
    marketer_perf = (
        User.objects.filter(role="marketer")
        .annotate(
            total_uploads=Count("uploaded_cars"),
            month_uploads=Count(
                "uploaded_cars",
                filter=Q(uploaded_cars__created_at__gte=month_start)
            ),
        )
        .order_by("-total_uploads")[:10]
    )

    # Sales agent performance
    sales_perf = (
        User.objects.filter(role="sales_agent")
        .annotate(
            total_handled=Count("handled_bookings"),
            confirmed_count=Count(
                "handled_bookings",
                filter=Q(handled_bookings__status="confirmed")
            ),
            completed_count=Count(
                "handled_bookings",
                filter=Q(handled_bookings__status="completed")
            ),
        )
        .order_by("-total_handled")[:10]
    )

    chart_data = _monthly_revenue_chart(6)
    booking_status_data = {
        "confirmed":  Booking.objects.filter(status="confirmed").count(),
        "pending":    Booking.objects.filter(status="pending").count(),
        "completed":  Booking.objects.filter(status="completed").count(),
        "cancelled":  Booking.objects.filter(status="cancelled").count(),
    }

    # Car inventory overview
    car_status_data = {
        "available": Car.objects.filter(status="available").count(),
        "scheduled": Car.objects.filter(status="scheduled").count(),
        "booked":    Car.objects.filter(status="booked").count(),
        "sold":      Car.objects.filter(status="sold").count(),
        "pending":   Car.objects.filter(status="pending").count(),
    }

    # Visit traffic
    total_visits   = VisitSchedule.objects.count()
    visits_this_m  = VisitSchedule.objects.filter(created_at__gte=month_start).count()
    car_views_this_m = CarView.objects.filter(viewed_at__gte=month_start).count()

    # Top performing cars
    top_cars = _cars_with_images(
        Car.objects.select_related("brand").order_by("-views_count")[:6]
    )
    staff_qs = User.objects.exclude(role__in=("customer",)).order_by("role", "full_name")
    staff_page = _paginate(request, staff_qs, 10, "staff_page")
    customer_qs = User.objects.filter(role="customer").order_by("-date_joined")
    customer_page = _paginate(request, customer_qs, 10, "customer_page")
    recent_messages_qs = SiteMessage.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=2)
    ).order_by("-created_at")
    recent_messages_page = _paginate(request, recent_messages_qs, 6, "msg_page")

    return {
        "view": "manager",
        "month_revenue": month_revenue,
        "month_revenue_fmt": _format_rwf(month_revenue),
        "marketer_perf": marketer_perf,
        "sales_perf": sales_perf,
        "chart_data_json": json.dumps(chart_data),
        "booking_status_data": json.dumps(booking_status_data),
        "car_status_data": json.dumps(car_status_data),
        "total_visits": total_visits,
        "visits_this_month": visits_this_m,
        "car_views_this_month": car_views_this_m,
        "top_cars": top_cars,
        "total_bookings": Booking.objects.count(),
        "month_bookings": Booking.objects.filter(created_at__gte=month_start).count(),
        "staff": staff_page.object_list,
        "staff_page": staff_page,
        "staff_count": staff_qs.count(),
        "customer_accounts": customer_page.object_list,
        "customer_page": customer_page,
        "customer_count": customer_qs.count(),
        "recent_messages_page": recent_messages_page,
        "recent_messages": recent_messages_page.object_list,
        "can_manage_staff": True,
        "can_manage_customers": True,
        "can_reply_messages": True,
    }


# ─────────────────────────────────────────────────────────────
# MARKETER CONTEXT
# ─────────────────────────────────────────────────────────────

def _ctx_marketer(request):
    user = request.user
    my_cars = Car.objects.filter(uploaded_by=user).select_related("brand").order_by("-created_at")

    # My stats
    my_total      = my_cars.count()
    my_live       = my_cars.filter(status__in=("available", "scheduled", "booked")).count()
    my_pending    = my_cars.filter(status="pending").count()
    my_booked     = my_cars.filter(status="booked").count()
    my_sold       = my_cars.filter(status="sold").count()
    my_rejected   = my_cars.filter(status="rejected").count()
    my_views      = my_cars.aggregate(v=Sum("views_count"))["v"] or 0
    avg_rating    = my_cars.aggregate(r=Avg("average_rating"))["r"] or 0

    # Active promotions
    active_promos = Promotion.objects.filter(
        is_active=True,
        end_date__gte=_today(),
        created_by=user,
    ).prefetch_related("cars")[:6]

    my_car_page = _paginate(request, my_cars, 12, "car_page")
    my_car_list = _cars_with_images(my_car_page.object_list)

    owner_form = CompanyCarOwnerForm(prefix="owner")
    car_form   = CarUploadForm(prefix="car")

    return {
        "view": "marketer",
        "my_total": my_total,
        "my_live": my_live,
        "my_pending": my_pending,
        "my_booked": my_booked,
        "my_sold": my_sold,
        "my_rejected": my_rejected,
        "my_views": my_views,
        "avg_rating": round(avg_rating, 1),
        "my_car_list": my_car_list,
        "my_car_page": my_car_page,
        "active_promos": active_promos,
        "owner_form": owner_form,
        "car_form": car_form,
    }


# ─────────────────────────────────────────────────────────────
# SALES AGENT CONTEXT
# ─────────────────────────────────────────────────────────────

def _ctx_sales(request):
    user = request.user
    month_start, _ = _this_month_range()

    # Bookings I handle
    my_bookings = Booking.objects.filter(handled_by=user).select_related("car", "customer")
    my_total    = my_bookings.count()
    my_confirmed = my_bookings.filter(status="confirmed").count()
    my_completed = my_bookings.filter(status="completed").count()
    my_pending   = my_bookings.filter(status="pending").count()
    my_month     = my_bookings.filter(created_at__gte=month_start).count()

    # Visit schedules I confirmed
    my_visits = VisitSchedule.objects.filter(confirmed_by=user).select_related("car", "customer")
    pending_visits = VisitSchedule.objects.filter(
        status__in=("pending", "confirmed")
    ).select_related("car", "customer").order_by("visit_date", "visit_time")[:15]

    # Unhandled bookings (pending, no handler)
    unhandled = Booking.objects.filter(
        status="pending", handled_by__isnull=True
    ).select_related("car", "customer").order_by("-created_at")[:10]

    # Recent bookings
    sales_bookings_page = _paginate(request, my_bookings.order_by("-created_at"), 10, "bp")
    recent_bookings = sales_bookings_page.object_list

    # Revenue from completed bookings I handled
    my_revenue = Payment.objects.filter(
        booking__handled_by=user, status="success"
    ).aggregate(total=Sum("amount"))["total"] or 0

    return {
        "view": "sales_agent",
        "my_total": my_total,
        "my_confirmed": my_confirmed,
        "my_completed": my_completed,
        "my_pending": my_pending,
        "my_month": my_month,
        "my_revenue_fmt": _format_rwf(my_revenue),
        "pending_visits": pending_visits,
        "unhandled_bookings": unhandled,
        "recent_bookings": recent_bookings,
        "sales_bookings_page": sales_bookings_page,
        "my_visits_count": my_visits.count(),
    }


# ─────────────────────────────────────────────────────────────
# ACCOUNTANT CONTEXT
# ─────────────────────────────────────────────────────────────

def _ctx_accountant(request):
    month_start, now = _this_month_range()

    # Revenue metrics
    total_revenue = Payment.objects.filter(status="success").aggregate(
        t=Sum("amount")
    )["t"] or 0
    month_revenue = Payment.objects.filter(
        status="success", paid_at__gte=month_start
    ).aggregate(t=Sum("amount"))["t"] or 0
    pending_total = Payment.objects.filter(status="pending").aggregate(
        t=Sum("amount")
    )["t"] or 0

    # Payment counts
    pending_payments_qs = Payment.objects.filter(status="pending").select_related(
        "customer", "booking__car", "schedule__car"
    ).order_by("-created_at")
    pending_payments_page = _paginate(request, pending_payments_qs, 12, "pp")
    pending_payments = pending_payments_page.object_list

    success_payments = Payment.objects.filter(status="success").select_related(
        "customer", "booking__car", "schedule__car", "processed_by"
    ).order_by("-paid_at")[:20]

    # Refunds
    pending_refunds = Refund.objects.filter(status="pending").select_related(
        "payment__customer", "requested_by"
    )
    total_refunded = Refund.objects.filter(status="processed").aggregate(
        t=Sum("amount")
    )["t"] or 0

    # Invoices
    recent_invoices = Invoice.objects.select_related(
        "payment__customer", "issued_to", "issued_by"
    ).order_by("-created_at")[:10]
    unsent_invoices = Invoice.objects.filter(is_sent=False).count()

    # Payment method breakdown
    method_breakdown = Payment.objects.filter(status="success").values(
        "payment_method"
    ).annotate(total=Sum("amount"), count=Count("id")).order_by("-total")

    # Revenue chart
    chart_data = _monthly_revenue_chart(6)

    return {
        "view": "accountant",
        "total_revenue_fmt": _format_rwf(total_revenue),
        "month_revenue_fmt": _format_rwf(month_revenue),
        "pending_total_fmt": _format_rwf(pending_total),
        "total_refunded_fmt": _format_rwf(total_refunded),
        "pending_payments": pending_payments,
        "pending_payments_page": pending_payments_page,
        "success_payments": success_payments,
        "pending_refunds": pending_refunds,
        "recent_invoices": recent_invoices,
        "unsent_invoices": unsent_invoices,
        "method_breakdown": method_breakdown,
        "chart_data_json": json.dumps(chart_data),
        "pending_count": pending_payments_qs.count(),
    }


# ─────────────────────────────────────────────────────────────
# INVENTORY MANAGER CONTEXT
# ─────────────────────────────────────────────────────────────

def _ctx_inventory(request):
    # All cars with metadata
    all_cars = Car.objects.select_related(
        "brand", "owner", "uploaded_by"
    ).prefetch_related("photos").order_by("-created_at")

    status_counts = {
        "available": all_cars.filter(status="available").count(),
        "scheduled": all_cars.filter(status="scheduled").count(),
        "booked":    all_cars.filter(status="booked").count(),
        "sold":      all_cars.filter(status="sold").count(),
        "pending":   all_cars.filter(status="pending").count(),
        "inactive":  all_cars.filter(status="inactive").count(),
        "rejected":  all_cars.filter(status="rejected").count(),
    }
    total_cars = all_cars.count()

    inv_page = _paginate(request, all_cars, 30, "ip")
    car_list = _cars_with_images(inv_page.object_list)

    # Cars needing attention
    no_photo_cars   = [c for c in all_cars if not c.photos.exists()][:10]
    featured_cars   = _cars_with_images(all_cars.filter(is_featured=True)[:8])

    # Brand distribution
    brand_dist = (
        CarBrand.objects.annotate(car_count=Count("cars")).order_by("-car_count")[:10]
    )

    return {
        "view": "inventory_manager",
        "status_counts": status_counts,
        "total_cars": total_cars,
        "car_list": car_list,
        "inv_page": inv_page,
        "no_photo_cars": no_photo_cars,
        "featured_cars": featured_cars,
        "brand_dist": brand_dist,
        "status_choices": Car.STATUS_CHOICES,
    }


# ─────────────────────────────────────────────────────────────
# CUSTOMER SUPPORT CONTEXT
# ─────────────────────────────────────────────────────────────

def _ctx_support(request):
    user = request.user

    # Tickets
    open_tickets = SupportTicket.objects.filter(
        status__in=("open", "in_progress")
    ).select_related("submitted_by", "assigned_to", "related_car").order_by("-created_at")

    my_tickets = SupportTicket.objects.filter(
        assigned_to=user
    ).select_related("submitted_by", "related_car").order_by("-created_at")

    # Stats
    total_open     = open_tickets.count()
    my_open        = my_tickets.filter(status__in=("open", "in_progress")).count()
    resolved_today = SupportTicket.objects.filter(
        resolved_at__date=_today()
    ).count()
    urgent_count   = open_tickets.filter(priority="urgent").count()
    high_count     = open_tickets.filter(priority="high").count()

    # Recent ticket replies by this agent
    my_replies = TicketReply.objects.filter(replied_by=user).order_by("-created_at")[:10]

    open_tickets_page = _paginate(request, open_tickets, 20, "tp")

    return {
        "view": "customer_support",
        "open_tickets": open_tickets_page.object_list,
        "open_tickets_page": open_tickets_page,
        "my_tickets": my_tickets[:10],
        "total_open": total_open,
        "my_open": my_open,
        "resolved_today": resolved_today,
        "urgent_count": urgent_count,
        "high_count": high_count,
        "my_replies": my_replies,
        "priority_choices": SupportTicket.PRIORITY,
        "status_choices": SupportTicket.STATUS,
    }


# ─────────────────────────────────────────────────────────────
# SHARED UTILITY: monthly revenue chart
# ─────────────────────────────────────────────────────────────

def _monthly_revenue_chart(months=6):
    """Return labels + values for the past N months."""
    now = _now()
    labels = []
    values = []
    for i in range(months - 1, -1, -1):
        dt = now - timedelta(days=30 * i)
        start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i == 0:
            end = now
        else:
            next_m = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = next_m
        total = Payment.objects.filter(
            status="success", paid_at__gte=start, paid_at__lt=end
        ).aggregate(t=Sum("amount"))["t"] or 0
        labels.append(start.strftime("%b %Y"))
        values.append(float(total))
    return {"labels": labels, "values": values}


def _cars_with_images(queryset):
    cars = list(queryset)
    car_ids = [c.id for c in cars]
    cover_map = {}
    for photo in CarPhoto.objects.filter(car_id__in=car_ids, is_cover=True):
        try:
            cover_map[photo.car_id] = photo.photo.url
        except Exception:
            pass
    first_map = {}
    for photo in CarPhoto.objects.filter(car_id__in=car_ids).order_by("order", "uploaded_at"):
        try:
            first_map.setdefault(photo.car_id, photo.photo.url)
        except Exception:
            pass
    return [
        {"car": c, "image": cover_map.get(c.id) or first_map.get(c.id, "")}
        for c in cars
    ]


# ─────────────────────────────────────────────────────────────
# ACTION VIEWS (AJAX/POST)
# ─────────────────────────────────────────────────────────────

@login_required
@require_POST
def approve_car(request, pk):
    """Admin/manager approves a pending car listing."""
    if request.user.role not in (*ADMIN_ROLES, "manager"):
        return JsonResponse({"error": "Forbidden"}, status=403)
    car = get_object_or_404(Car, pk=pk)
    car.status = "available"
    car.approved_by = request.user
    car.approved_at = timezone.now()
    car.save(update_fields=["status", "approved_by", "approved_at"])
    AuditLog.objects.create(
        user=request.user, action="approved", model_affected="Car",
        object_id=str(car.pk),
        description=f"Approved car listing: {car.title}",
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    messages.success(request, f"{car.title} approved and now live.")
    return redirect("homepage:dashboard")


@login_required
@require_POST
def reject_car(request, pk):
    """Admin/manager rejects a pending car listing."""
    if request.user.role not in (*ADMIN_ROLES, "manager"):
        return JsonResponse({"error": "Forbidden"}, status=403)
    car = get_object_or_404(Car, pk=pk)
    car.status = "rejected"
    car.save(update_fields=["status"])
    AuditLog.objects.create(
        user=request.user, action="rejected", model_affected="Car",
        object_id=str(car.pk),
        description=f"Rejected car listing: {car.title}",
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    messages.success(request, f"{car.title} has been rejected.")
    return redirect("homepage:dashboard")


@login_required
@require_POST
def delete_car(request, pk):
    """Admin deletes a car listing."""
    if request.user.role not in ADMIN_ROLES:
        messages.error(request, "Only admins can delete listings.")
        return redirect("homepage:dashboard")
    
    car = get_object_or_404(Car, pk=pk)
    title = car.title
    
    try:
        car.delete()
        AuditLog.objects.create(
            user=request.user, action="deleted", model_affected="Car",
            object_id=str(car.pk),
            description=f"Deleted car listing: {title}",
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        messages.success(request, f"{title} has been permanently deleted.")
        
    except ProtectedError as e:
        booking_count = car.bookings.count()
        car.status = "inactive"
        car.is_featured = False
        car.save(update_fields=["status", "is_featured"])
        messages.warning(
            request,
            f"'{title}' could not be hard-deleted because it has {booking_count} related booking(s). "
            "It has been removed from the platform by marking it inactive."
        )
        AuditLog.objects.create(
            user=request.user, action="updated", model_affected="Car",
            object_id=str(car.pk),
            description=f"Archived car after delete fallback: {title} - has {booking_count} existing bookings",
            ip_address=request.META.get("REMOTE_ADDR"),
        )
    
    return redirect("homepage:dashboard")


@login_required
@require_POST
def update_car_status(request, pk):
    """Inventory manager updates car status."""
    if request.user.role not in (*INVENTORY_ROLES, *ADMIN_ROLES):
        messages.error(request, "Forbidden.")
        return redirect("homepage:dashboard")
    car = get_object_or_404(Car, pk=pk)
    new_status = request.POST.get("status")
    valid = [s[0] for s in Car.STATUS_CHOICES]
    if new_status not in valid:
        messages.error(request, "Invalid status.")
        return redirect("homepage:dashboard")
    old_status = car.status
    car.status = new_status
    car.save(update_fields=["status"])
    AuditLog.objects.create(
        user=request.user, action="updated", model_affected="Car",
        object_id=str(car.pk),
        description=f"Status changed from {old_status} → {new_status}: {car.title}",
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    messages.success(request, f"{car.title} status updated to {new_status}.")
    return redirect("homepage:dashboard")


@login_required
@require_POST
def return_car_to_platform(request, pk):
    """Return a car to public availability for permitted staff."""
    allowed_roles = (*ADMIN_ROLES, "manager", "sales_agent", "accountant")
    if request.user.role not in allowed_roles:
        messages.error(request, "You do not have permission to return this car to the platform.")
        return redirect("homepage:dashboard")

    car = get_object_or_404(Car, pk=pk)
    if car.status == "sold":
        messages.error(request, "Sold cars cannot be returned to the platform.")
        return redirect("homepage:dashboard")

    old_status = car.status
    car.status = "available"
    car.save(update_fields=["status"])
    AuditLog.objects.create(
        user=request.user, action="updated", model_affected="Car",
        object_id=str(car.pk),
        description=f"Returned car to platform from {old_status}: {car.title}",
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    messages.success(request, f"{car.title} is live on the platform again.")
    return redirect(request.POST.get("next") or "homepage:dashboard")


@login_required
@require_POST
def confirm_payment_dashboard(request, pk):
    """Accountant confirms a payment."""
    if request.user.role not in (*FINANCE_ROLES,):
        messages.error(request, "Forbidden.")
        return redirect("homepage:dashboard")
    payment = get_object_or_404(Payment, pk=pk)
    payment.status = "success"
    payment.processed_by = request.user
    payment.paid_at = timezone.now()
    payment.save(update_fields=["status", "processed_by", "paid_at"])

    # Auto-confirm booking or schedule
    if payment.booking and payment.booking.status == "pending":
        payment.booking.status = "confirmed"
        payment.booking.handled_by = request.user
        payment.booking.save(update_fields=["status", "handled_by"])
    if payment.schedule and payment.schedule.status == "pending":
        payment.schedule.status = "confirmed"
        payment.schedule.fee_paid = True
        payment.schedule.confirmed_by = request.user
        payment.schedule.save(update_fields=["status", "fee_paid", "confirmed_by"])

    _ensure_invoice_for_payment(payment, request.user, request=request)

    twilio_sent = twilio_whatsapp_service.send_payment_confirmation(payment, request=request)
    if not twilio_sent:
        messages.warning(request, "Payment was confirmed, but the WhatsApp confirmation could not be sent. Please check the Twilio settings and WhatsApp logs.")

    AuditLog.objects.create(
        user=request.user, action="updated", model_affected="Payment",
        object_id=str(payment.pk),
        description=f"Confirmed payment {payment.payment_number} — {payment.amount} RWF",
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    messages.success(request, f"Payment {payment.payment_number} confirmed.")
    return _redirect_after_payment_confirmation(payment, "homepage:dashboard")


@login_required
@require_POST
def approve_refund(request, pk):
    """Accountant approves a refund."""
    if request.user.role not in FINANCE_ROLES:
        messages.error(request, "Forbidden.")
        return redirect("homepage:dashboard")
    refund = get_object_or_404(Refund, pk=pk)
    refund.status = "processed"
    refund.approved_by = request.user
    refund.processed_at = timezone.now()
    refund.save(update_fields=["status", "approved_by", "processed_at"])
    messages.success(request, f"Refund of {_format_rwf(refund.amount)} processed.")
    return redirect("homepage:dashboard")


@login_required
@require_POST
def assign_ticket(request, pk):
    """Customer support self-assigns a ticket."""
    if request.user.role not in (*SUPPORT_ROLES, *ADMIN_ROLES):
        messages.error(request, "Forbidden.")
        return redirect("homepage:dashboard")
    ticket = get_object_or_404(SupportTicket, pk=pk)
    ticket.assigned_to = request.user
    ticket.status = "in_progress"
    ticket.save(update_fields=["assigned_to", "status"])
    messages.success(request, f"Ticket {ticket.ticket_number} assigned to you.")
    return redirect("homepage:dashboard")


@login_required
@require_POST
def reply_ticket(request, pk):
    """Add a reply to a support ticket."""
    if request.user.role not in (*SUPPORT_ROLES, *ADMIN_ROLES):
        messages.error(request, "Forbidden.")
        return redirect("homepage:dashboard")
    ticket = get_object_or_404(SupportTicket, pk=pk)
    message_text = request.POST.get("message", "").strip()
    if message_text:
        TicketReply.objects.create(ticket=ticket, replied_by=request.user, message=message_text)
        ticket.status = "in_progress"
        ticket.save(update_fields=["status"])
        messages.success(request, "Reply sent.")
    else:
        messages.error(request, "Reply cannot be empty.")
    return redirect("homepage:dashboard")


@login_required
@require_POST
def reply_site_message(request, pk):
    """Reply to a customer site message."""
    if request.user.role not in (*ADMIN_ROLES, "manager", "customer_support"):
        messages.error(request, "Forbidden.")
        return redirect("homepage:dashboard")

    site_message = get_object_or_404(SiteMessage, pk=pk)
    reply_text = request.POST.get("message", "").strip()
    if not reply_text:
        messages.error(request, "Reply cannot be empty.")
        return redirect("homepage:dashboard")

    try:
        _send_site_message_reply(site_message, reply_text, request.user)
    except Exception:
        messages.error(request, "Reply could not be sent. Please check email settings.")
        return redirect("homepage:dashboard")

    site_message.reply_message = reply_text
    site_message.replied_by = request.user
    site_message.replied_at = timezone.now()
    site_message.status = "replied"
    site_message.save(update_fields=["reply_message", "replied_by", "replied_at", "status"])

    email_sent = _send_site_message_reply(site_message, reply_text, request.user) > 0

    AuditLog.objects.create(
        user=request.user,
        action="updated",
        model_affected="SiteMessage",
        object_id=str(site_message.pk),
        description=f"Replied to site message from {site_message.name}",
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    if email_sent:
        messages.success(request, "Reply sent successfully.")
    else:
        messages.success(request, "Reply saved successfully, but the email notification could not be delivered.")
    return redirect("homepage:dashboard")


@login_required
@require_POST
def resolve_ticket(request, pk):
    """Mark a ticket as resolved."""
    if request.user.role not in (*SUPPORT_ROLES, *ADMIN_ROLES):
        messages.error(request, "Forbidden.")
        return redirect("homepage:dashboard")
    ticket = get_object_or_404(SupportTicket, pk=pk)
    ticket.status = "resolved"
    ticket.resolved_at = timezone.now()
    ticket.save(update_fields=["status", "resolved_at"])
    messages.success(request, f"Ticket {ticket.ticket_number} resolved.")
    return redirect("homepage:dashboard")


@login_required
@require_POST
def handle_booking(request, pk):
    """Sales agent takes ownership of a booking."""
    if request.user.role not in (*SALES_ROLES,):
        messages.error(request, "Forbidden.")
        return redirect("homepage:dashboard")
    booking = get_object_or_404(Booking, pk=pk)
    booking.handled_by = request.user
    if booking.status == "pending":
        booking.status = "confirmed"
    booking.save(update_fields=["handled_by", "status"])
    AuditLog.objects.create(
        user=request.user, action="updated", model_affected="Booking",
        object_id=str(booking.pk),
        description=f"Sales agent {request.user.full_name} took booking {booking.booking_number}",
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    messages.success(request, f"Booking {booking.booking_number} is now yours to handle.")
    return redirect("homepage:dashboard")


@login_required
@require_POST
def complete_booking(request, pk):
    """Sales agent marks a booking as completed (sold)."""
    if request.user.role not in (*SALES_ROLES,):
        messages.error(request, "Forbidden.")
        return redirect("homepage:dashboard")
    booking = get_object_or_404(Booking, pk=pk)
    booking.status = "completed"
    booking.save(update_fields=["status"])   # triggers car.mark_as_sold()
    messages.success(request, f"Booking {booking.booking_number} completed. Car marked as sold.")
    return redirect("homepage:dashboard")


@login_required
@require_POST
def confirm_visit(request, pk):
    """Sales agent confirms a visit schedule."""
    if request.user.role not in (*SALES_ROLES,):
        messages.error(request, "Forbidden.")
        return redirect("homepage:dashboard")
    schedule = get_object_or_404(VisitSchedule, pk=pk)
    schedule.status = "confirmed"
    schedule.confirmed_by = request.user
    schedule.save(update_fields=["status", "confirmed_by"])
    messages.success(request, f"Visit {schedule.schedule_number} confirmed.")
    return redirect("homepage:dashboard")


@login_required
@require_POST
def sales_reject_visit(request, pk):
    """Sales agent cancels a visit that is not ready to proceed."""
    if request.user.role not in (*SALES_ROLES,):
        messages.error(request, "Forbidden.")
        return redirect("homepage:dashboard")
    schedule = get_object_or_404(VisitSchedule, pk=pk)
    schedule.status = "cancelled"
    schedule.save(update_fields=["status"])
    messages.success(request, f"Visit {schedule.schedule_number} has been cancelled.")
    return redirect("homepage:dashboard")


@login_required
@require_POST
def deactivate_user(request, pk):
    """Admin deactivates a user account."""
    if request.user.role not in ADMIN_ROLES:
        messages.error(request, "Forbidden.")
        return redirect("homepage:dashboard")
    target = get_object_or_404(User, pk=pk)
    if target == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("homepage:dashboard")
    target.is_active = False
    target.save(update_fields=["is_active"])
    AuditLog.objects.create(
        user=request.user, action="updated", model_affected="CustomUser",
        object_id=str(target.pk),
        description=f"Deactivated account: {target.email}",
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    messages.success(request, f"{target.full_name}'s account deactivated.")
    return redirect("homepage:dashboard")


@login_required
@require_POST
def activate_user(request, pk):
    """Admin re-activates a user account."""
    if request.user.role not in ADMIN_ROLES:
        messages.error(request, "Forbidden.")
        return redirect("homepage:dashboard")
    target = get_object_or_404(User, pk=pk)
    target.is_active = True
    target.save(update_fields=["is_active"])
    messages.success(request, f"{target.full_name}'s account re-activated.")
    return redirect("homepage:dashboard")


@login_required
@require_POST
def delete_user(request, pk):
    """Admin permanently deletes a user account."""
    if request.user.role not in ADMIN_ROLES:
        messages.error(request, "Forbidden.")
        return redirect("homepage:dashboard")
    target = get_object_or_404(User, pk=pk)
    if target == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect("homepage:dashboard")
    email = target.email
    AuditLog.objects.create(
        user=request.user, action="deleted", model_affected="CustomUser",
        object_id=str(target.pk),
        description=f"Permanently deleted user: {email}",
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    try:
        target.delete()
        messages.success(request, f"User {email} permanently deleted.")
    except ProtectedError:
        target.is_active = False
        target.save(update_fields=["is_active"])
        messages.warning(
            request,
            f"User {email} has related records, so the account was deactivated instead of fully deleted.",
        )
    return redirect("homepage:dashboard")


@login_required
@require_POST
def reset_user_password(request, pk):
    """Send a password reset email for a customer or staff account."""
    if request.user.role not in ADMIN_ROLES:
        messages.error(request, "Forbidden.")
        return redirect("homepage:dashboard")

    target = get_object_or_404(User, pk=pk)
    if not target.email:
        messages.error(request, "This account does not have an email address.")
        return redirect("homepage:dashboard")

    reset_form = PasswordResetForm(data={"email": target.email})
    if reset_form.is_valid():
        reset_form.save(
            request=request,
            use_https=request.is_secure(),
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
        )
        messages.success(request, f"Password reset email sent to {target.full_name}.")
    else:
        messages.error(request, "Could not send a password reset email for that account.")
    return redirect("homepage:dashboard")


@login_required
def mark_notification_read(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    n.is_read = True
    n.save(update_fields=["is_read"])
    return JsonResponse({"ok": True})


@login_required
def notifications_list(request):
    notifs = Notification.objects.filter(user=request.user).order_by("-created_at")[:30]
    data = [
        {
            "id": str(n.id),
            "title": n.title,
            "message": n.message,
            "type": n.notif_type,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifs
    ]
    return JsonResponse({"notifications": data})


@login_required
def download_invoice(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related(
            "payment__booking__car",
            "payment__schedule__car",
            "issued_to",
            "issued_by",
        ),
        pk=pk,
    )
    if not _can_access_invoice(request.user, invoice):
        messages.error(request, "You do not have permission to access that invoice.")
        return redirect("homepage:profile")

    if invoice.pdf_file:
        return FileResponse(
            invoice.pdf_file.open("rb"),
            as_attachment=True,
            filename=f"{invoice.invoice_number}.pdf",
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=40, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    payment = invoice.payment
    booking = payment.booking
    schedule = payment.schedule
    related_car = booking.car if booking else schedule.car if schedule else None

    title_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=colors.HexColor("#0f766e"),
        spaceAfter=14,
    )
    meta_style = ParagraphStyle(
        "InvoiceMeta",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#5b6475"),
        spaceAfter=6,
    )

    story.append(Paragraph(f"Invoice {invoice.invoice_number}", title_style))
    story.append(Paragraph(f"Issued to: {invoice.issued_to.full_name}", styles["Normal"]))
    story.append(Paragraph(f"Email: {invoice.issued_to.email}", styles["Normal"]))
    story.append(Paragraph(f"Issued on: {invoice.created_at.strftime('%d %B %Y %H:%M')}", meta_style))
    if invoice.issued_by:
        story.append(Paragraph(f"Issued by: {invoice.issued_by.full_name}", meta_style))
    story.append(Spacer(1, 10))

    data = [
        ["Invoice #", invoice.invoice_number],
        ["Payment #", payment.payment_number],
        ["Amount", _format_rwf(payment.amount)],
        ["Method", payment.get_payment_method_display()],
        ["Purpose", payment.get_purpose_display()],
        ["Payment status", payment.get_status_display()],
        ["Paid at", payment.paid_at.strftime("%d %B %Y %H:%M") if payment.paid_at else "Verified"],
    ]
    if booking:
        data.extend([
            ["Booking ref", booking.booking_number],
            ["Booking status", booking.get_status_display()],
        ])
    if schedule:
        data.extend([
            ["Visit ref", schedule.schedule_number],
            ["Visit date", f"{schedule.visit_date.strftime('%d %B %Y')} {schedule.visit_time.strftime('%H:%M')}"],
        ])
    if related_car:
        data.extend([
            ["Car", related_car.title],
            ["Location", f"{related_car.district}, {related_car.province}"],
        ])

    table = Table(data, colWidths=[130, 360])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6fffb")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#152238")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c7d2e3")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(table)
    story.append(Spacer(1, 14))
    story.append(Paragraph("Thank you for using On Call Driver.", meta_style))

    doc.build(story)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"{invoice.invoice_number}.pdf")


#services webpage

def get_site_settings():
    """Get or create site settings singleton"""
    settings = SiteSettings.objects.first()
    if not settings:
        settings = SiteSettings.objects.create()
    return settings


def log_audit(user, action, model_affected, object_id='', description='', request=None):
    """Helper to create audit logs"""
    from .models import AuditLog
    AuditLog.objects.create(
        user=user,
        action=action,
        model_affected=model_affected,
        object_id=str(object_id),
        description=description,
        ip_address=request.META.get('REMOTE_ADDR') if request else None
    )


def services(request):
    """Main services page showing all offerings, stats, categories, testimonials"""
    site_settings = get_site_settings()
    
    # Calculate statistics
    total_cars = Car.objects.filter(status='available').count()
    total_bookings = Booking.objects.filter(status='confirmed').count()
    total_customers = CustomUser.objects.filter(role='customer').count()
    provinces_count = Car.objects.filter(status='available').values('province').distinct().count()
    
    stats = {
        'total_cars': total_cars or 500,
        'total_bookings': total_bookings or 1200,
        'total_customers': total_customers or 800,
        'provinces': provinces_count or 5,
    }
    
    # Category counts
    category_counts = {
        'sedans': Car.objects.filter(status='available', model__icontains='sedan').count() or 42,
        'suvs': Car.objects.filter(status='available', drive_type__in=['awd', '4wd']).count() or 85,
        'vans': Car.objects.filter(status='available', seats__gte=7).count() or 28,
        'hybrids': Car.objects.filter(status='available', fuel_type__in=['hybrid', 'electric']).count() or 35,
        'luxury': Car.objects.filter(status='available', is_featured=True).count() or 18,
        'trucks': Car.objects.filter(status='available', model__icontains='truck').count() or 22,
        'negotiable': Car.objects.filter(status='available', is_negotiable=True).count() or 64,
        'new': Car.objects.filter(status='available', created_at__gte=timezone.now() - timedelta(days=7)).count() or 12,
    }
    
    # Get recent testimonials
    testimonials = CarReview.objects.filter(is_approved=True).select_related('customer', 'car').order_by('-created_at')[:6]
    
    context = {
        'site_name': site_settings.site_name,
        'site_logo': site_settings.site_logo,
        'stats': stats,
        'category_counts': category_counts,
        'testimonials': testimonials,
        'site': site_settings,
    }
    
    return render(request, 'homepage/service.html', context)



def _site_ctx():
    """Minimal site context helper (reuse your existing get_site_context if preferred)."""
    s = SiteSettings.objects.first()
    logo = ""
    if s and s.site_logo:
        try:
            logo = s.site_logo.url
        except Exception:
            pass
    return {
        "site": s,
        "site_name": s.site_name if s else "On Call Driver",
        "site_logo": logo,
    }
 
 
def about_us(request):
    """
    About Us page view.
    Renders company story, team, stats, and a public contact/review form.
    POST handles the SiteMessage submission (and optionally a star review if user is authenticated).
    """
    cleanup_expired_site_messages()
    # ── Platform stats for the hero strip ──
    total_cars      = Car.objects.filter(status__in=("available", "scheduled", "booked", "sold")).count()
    total_sold      = Car.objects.filter(status="sold").count()
    total_customers = CustomUser.objects.filter(role="customer", is_active=True).count()
    avg_rating_qs   = CarReview.objects.filter(is_approved=True).aggregate(avg=Avg("rating"))
    avg_rating      = round(avg_rating_qs["avg"] or 4.8, 1)
    total_bookings  = Booking.objects.count()
 
    # ── Latest approved reviews for the testimonial wall ──
    recent_reviews = (
        CarReview.objects
        .filter(is_approved=True, body__gt="")
        .select_related("customer", "car")
        .order_by("-created_at")[:6]
    )
 
    # ── Handle contact / feedback form POST ──
    form_errors = {}
    form_data   = {}
 
    if request.method == "POST":
        name    = request.POST.get("name", "").strip()
        email   = request.POST.get("email", "").strip()
        phone   = request.POST.get("phone", "").strip()
        subject = request.POST.get("subject", "").strip()
        msg     = request.POST.get("message", "").strip()
 
        # Simple validation
        if not name:
            form_errors["name"] = "Your name is required."
        if not email or "@" not in email:
            form_errors["email"] = "A valid email address is required."
        if not subject:
            form_errors["subject"] = "Please enter a subject."
        if not msg or len(msg) < 10:
            form_errors["message"] = "Message must be at least 10 characters."
 
        if not form_errors:
            # Import here to avoid circular issues if model is in same file
            try:
                from .models import SiteMessage
                SiteMessage.objects.create(
                    name=name,
                    email=email,
                    phone=phone,
                    subject=subject,
                    message=msg,
                )
            except ImportError:
                # SiteMessage not yet migrated — silently pass, still show success
                pass
 
            messages.success(
                request,
                f"Thank you, {name}! Your message has been received. We'll get back to you shortly."
            )
            return redirect("homepage:about_us")
        else:
            # Re-populate form with entered data so user doesn't retype
            form_data = {
                "name": name, "email": email,
                "phone": phone, "subject": subject, "message": msg,
            }
 
    context = {
        **_site_ctx(),
        # Stats
        "total_cars":      total_cars,
        "total_sold":      total_sold,
        "total_customers": total_customers,
        "avg_rating":      avg_rating,
        "total_bookings":  total_bookings,
        # Reviews
        "recent_reviews": recent_reviews,
        # Form
        "form_errors": form_errors,
        "form_data":   form_data,
    }
    return render(request, "homepage/about_us.html", context)


def contact(request):
    """
    Contact page view - handles contact form submissions.
    Displays contact information and processes messages from visitors.
    """
    cleanup_expired_site_messages()
    site_settings = SiteSettings.objects.first()
    
    # Get site settings for context
    site_name = site_settings.site_name if site_settings else "On Call Driver"
    contact_phone = site_settings.contact_phone if site_settings else "+250 788 123 456"
    contact_email = site_settings.contact_email if site_settings else "info@ocdltd.rw"
    address = site_settings.address if site_settings else "Kigali, Rwanda"
    whatsapp_number = site_settings.whatsapp_number if site_settings else "250788123456"
    facebook_url = site_settings.facebook_url if site_settings else "#"
    instagram_url = site_settings.instagram_url if site_settings else "#"
    twitter_url = site_settings.twitter_url if site_settings else "#"
    linkedin_url = getattr(site_settings, 'linkedin_url', '#') if site_settings else "#"
    
    # Get total cars for stats display
    total_cars = Car.objects.filter(status__in=["available", "scheduled", "booked"]).count()
    total_customers = CustomUser.objects.filter(role="customer", is_active=True).count()
    total_bookings = Booking.objects.count()
    avg_rating_qs = CarReview.objects.filter(is_approved=True).aggregate(avg=Avg("rating"))
    avg_rating = round(avg_rating_qs["avg"] or 4.8, 1)
    
    # Handle POST request (form submission)
    form_errors = {}
    form_data = {}
    
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()
        
        # Validation
        if not name:
            form_errors["name"] = "Please enter your full name."
        elif len(name) < 3:
            form_errors["name"] = "Name must be at least 3 characters."
            
        if not email:
            form_errors["email"] = "Please enter your email address."
        elif "@" not in email or "." not in email:
            form_errors["email"] = "Please enter a valid email address."
            
        if not subject:
            form_errors["subject"] = "Please enter a subject."
        elif len(subject) < 3:
            form_errors["subject"] = "Subject must be at least 3 characters."
            
        if not message:
            form_errors["message"] = "Please enter your message."
        elif len(message) < 10:
            form_errors["message"] = "Message must be at least 10 characters."
        
        # Store form data for repopulation on error
        form_data = {
            "name": name,
            "email": email,
            "phone": phone,
            "subject": subject,
            "message": message,
        }
        
        if not form_errors:
            # Save to database using SiteMessage model
            try:
                SiteMessage.objects.create(
                    name=name,
                    email=email,
                    phone=phone,
                    subject=subject,
                    message=message,
                    ip_address=get_client_ip(request),
                )
            except Exception as e:
                # If SiteMessage doesn't exist, log error but still show success
                print(f"Could not save message: {e}")
            
            # Send email notification to admin (optional)
            try:
                admin_subject = f"[Contact] {subject} from {name}"
                admin_message = f"""
Name: {name}
Email: {email}
Phone: {phone or 'Not provided'}
Subject: {subject}

Message:
{message}
                """
                send_mail(
                    subject=admin_subject,
                    message=admin_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[contact_email],
                    fail_silently=True,
                )
            except Exception:
                pass  # Don't break user experience if email fails
            
            messages.success(
                request,
                f"Thank you, {name}! Your message has been sent successfully. We'll get back to you within 24 hours."
            )
            return redirect("homepage:contact")
    
    # FAQ data - can be moved to database later
    faqs = [
        {"question": "What documents do I need to rent a car?", 
         "answer": "You'll need a valid driver's license, national ID or passport, and a valid payment method. For international renters, an international driving permit is recommended."},
        {"question": "Do you offer driver training for beginners?",
         "answer": "Yes! Our certified instructors provide personalized driving lessons for new drivers. We focus on building confidence, road safety, and practical skills."},
        {"question": "What payment methods do you accept?",
         "answer": "We accept MTN MoMo, Airtel Money, Visa/Mastercard, and bank transfers. Cash payments are also accepted at our physical office."},
        {"question": "Can I cancel or reschedule my booking?",
         "answer": "Yes, cancellations made 48 hours before pickup receive a full refund. Rescheduling is free up to 24 hours before your booking."},
        {"question": "Do you provide cars for long-term rental?",
         "answer": "Absolutely. We offer competitive monthly and yearly rental plans with dedicated support and maintenance included."},
        {"question": "Is insurance included with rentals?",
         "answer": "Yes, basic insurance is included with every rental. Additional coverage options are available for comprehensive protection."},
    ]
    
    context = {
        **get_site_context(),
        "site_name": site_name,
        "contact_phone": contact_phone,
        "contact_email": contact_email,
        "address": address,
        "whatsapp_number": whatsapp_number,
        "facebook_url": facebook_url,
        "instagram_url": instagram_url,
        "twitter_url": twitter_url,
        "linkedin_url": linkedin_url,
        "total_cars": total_cars,
        "total_customers": total_customers,
        "total_bookings": total_bookings,
        "avg_rating": avg_rating,
        "faqs": faqs,
        "form_errors": form_errors,
        "form_data": form_data,
    }
    return render(request, "homepage/contact.html", context)


def get_client_ip(request):
    """Helper to get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip



#helps aadmin to add site settings like logo, contact info, business rules etc
@login_required
@user_passes_test(lambda u: u.role in ('super_admin', 'admin'))
def site_settings_view(request):
    """
    Admin panel for managing site settings including:
    - Site logo and name
    - Hero banner
    - Contact information
    - Social media links
    - Business rules (fees, commissions)
    """
    # Get or create site settings (enforce singleton)
    site_settings = SiteSettings.objects.first()
    if not site_settings:
        site_settings = SiteSettings.objects.create()
    
    if request.method == 'POST':
        form = SiteSettingsForm(request.POST, request.FILES, instance=site_settings)
        if form.is_valid():
            form.save()
            
            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action='updated',
                model_affected='SiteSettings',
                object_id=str(site_settings.pk),
                description='Updated site settings (logo, contact info, business rules)',
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            
            messages.success(request, 'Site settings have been successfully updated!')
            return redirect('homepage:site_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SiteSettingsForm(instance=site_settings)
    
    # Get current values for preview
    context = {
        **get_site_context(),
        'form': form,
        'site_settings': site_settings,
        'section': 'site_settings',
    }
    
    return render(request, 'homepage/site_settings.html', context)


@login_required
@user_passes_test(lambda u: u.role in ('super_admin', 'admin'))
def site_settings_remove_logo(request):
    """
    Remove the current site logo
    """
    if request.method == 'POST':
        site_settings = SiteSettings.objects.first()
        if site_settings and site_settings.site_logo:
            # Delete the file from storage
            site_settings.site_logo.delete(save=False)
            site_settings.site_logo = None
            site_settings.save()
            
            messages.success(request, 'Site logo has been removed.')
        else:
            messages.warning(request, 'No logo to remove.')
    
    return redirect('homepage:site_settings')


@login_required
@user_passes_test(lambda u: u.role in ('super_admin', 'admin'))
def site_settings_remove_banner(request):
    """
    Remove the current hero banner
    """
    if request.method == 'POST':
        site_settings = SiteSettings.objects.first()
        if site_settings and site_settings.hero_banner:
            site_settings.hero_banner.delete(save=False)
            site_settings.hero_banner = None
            site_settings.save()
            
            messages.success(request, 'Hero banner has been removed.')
        else:
            messages.warning(request, 'No banner to remove.')
    
    return redirect('homepage:site_settings')


@login_required
def manager_report_pdf(request):
    """Generate PDF report using reportlab."""
    
    if request.user.role not in ('super_admin', 'admin', 'manager'):
        messages.error(request, "You don't have permission to access this report.")
        return redirect('homepage:dashboard')
    
    report_type = request.GET.get("type", "bookings")
    
    # Create file buffer
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    
    # Container for story elements
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#f5a623'),
        alignment=TA_CENTER,
        spaceAfter=30
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.black,
        spaceAfter=12
    )
    
    # Add title
    if report_type == "bookings":
        title = "Bookings Report"
        story.append(Paragraph(title, title_style))
        
        # Get data
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        bookings = Booking.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).select_related('car', 'customer')[:50]
        
        # Create table data
        table_data = [['Booking #', 'Customer', 'Car', 'Amount (RWF)', 'Status', 'Date']]
        total_revenue = 0
        
        for booking in bookings:
            table_data.append([
                booking.booking_number,
                booking.customer.full_name[:30],
                booking.car.title[:30],
                f"{int(booking.amount_paid):,}",
                booking.get_status_display(),
                booking.created_at.strftime('%Y-%m-%d')
            ])
            total_revenue += booking.amount_paid
        
        # Add summary
        story.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
        story.append(Paragraph(f"Total Bookings: {bookings.count()}", styles['Normal']))
        story.append(Paragraph(f"Total Revenue: {int(total_revenue):,} RWF", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Create table
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5a623')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        story.append(table)
        
    elif report_type == "schedules":
        title = "Visit Schedules Report"
        story.append(Paragraph(title, title_style))
        
        # Get data
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        schedules = VisitSchedule.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).select_related('car', 'customer')[:50]
        
        # Create table data
        table_data = [['Schedule #', 'Customer', 'Car', 'Visit Date', 'Status', 'Fee Paid']]
        
        for schedule in schedules:
            table_data.append([
                schedule.schedule_number,
                schedule.customer.full_name[:30],
                schedule.car.title[:30],
                f"{schedule.visit_date} {schedule.visit_time}",
                schedule.get_status_display(),
                'Yes' if schedule.fee_paid else 'No'
            ])
        
        # Add summary
        story.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
        story.append(Paragraph(f"Total Schedules: {schedules.count()}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Create table
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5a623')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        story.append(table)
    else:
        payment_status = "success" if report_type in ("payments", "payments_paid", "paid") else "pending"
        title = "Paid Payments Report" if payment_status == "success" else "Pending Payments Report"
        story.append(Paragraph(title, title_style))

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        payments = (
            Payment.objects.filter(
                status=payment_status,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            )
            .select_related("customer", "booking__car", "schedule__car")
            .order_by("-created_at")[:50]
        )

        table_data = [["Payment #", "Customer", "Purpose", "Amount (RWF)", "Status", "Date"]]
        total_amount = 0

        for payment in payments:
            table_data.append([
                payment.payment_number,
                payment.customer.full_name[:30],
                payment.get_purpose_display(),
                f"{int(payment.amount):,}",
                payment.get_status_display(),
                payment.created_at.strftime("%Y-%m-%d"),
            ])
            if payment_status == "success":
                total_amount += payment.amount

        story.append(Paragraph(f"Period: {start_date} to {end_date}", styles["Normal"]))
        story.append(Paragraph(f"Status: {payment_status.title()}", styles["Normal"]))
        story.append(Paragraph(f"Total Payments: {payments.count()}", styles["Normal"]))
        if payment_status == "success":
            story.append(Paragraph(f"Total Revenue: {int(total_amount):,} RWF", styles["Normal"]))
        story.append(Spacer(1, 20))

        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5a623")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
        ]))
        story.append(table)

    # Build PDF
    doc.build(story)
    
    buffer.seek(0)
    
    return FileResponse(buffer, as_attachment=False, filename=f'{report_type}_report.pdf')
