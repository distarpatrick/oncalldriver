from django.urls import path
from . import views
from .whatsapp_webhook import whatsapp_webhook
app_name = "homepage"

urlpatterns = [
    path("", views.index, name="index"),
    path("cars/", views.cars, name="cars"),
    path("login/", views.auth_view, name="auth"),
    path("register/", views.auth_view, name="register"),
    path("make-book-visit/", views.make_book_visit, name="make_book_visit"),
    path("password-reset/request/", views.password_reset_request, name="password_reset_request"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("profile/security/", views.profile_security, name="profile_security"),
    path("profile/visits/<uuid:schedule_id>/update/", views.update_visit_schedule, name="update_visit_schedule"),
    path("profile/visits/<uuid:schedule_id>/delete/", views.delete_visit_schedule, name="delete_visit_schedule"),
    path("profile/wishlist/<int:wishlist_id>/delete/", views.delete_wishlist, name="delete_wishlist"),
    path("profile/payments/<uuid:payment_id>/confirm/", views.confirm_payment, name="confirm_payment"),
    path("profile/invoices/<uuid:pk>/download/", views.download_invoice, name="download_invoice"),
    path("cars/upload/", views.upload_car, name="upload_car"),
    path("search/", views.global_search, name="global_search"),
    
  
    # Main marketplace listing page
    # URL: /cars/
    path("cars_on_the_market/",views.car_list,name="car_list"),

    # Single car detail page
    path("<uuid:pk>/",views.car_detail,name="car_detail",),


    # Book a car (POST only)
    # Otherwise → redirects back to car_list with a Django message
    path("<uuid:pk>/book/",views.book_car,name="book_car"),
    # Schedule a visit (POST only)
    # URL: /cars/<uuid:pk>/schedule/
    # Accepts AJAX → returns JSON; otherwise redirects

    path("<uuid:pk>/schedule/",views.schedule_visit, name="schedule_visit",
    ),
    # Toggle wishlist for a car (POST, login required)
    # URL: /cars/<uuid:pk>/wishlist/
    # Always returns JSON: { wishlisted: bool, message: str }
 
    path(
        "<uuid:pk>/wishlist/",
        views.toggle_wishlist,
        name="toggle_wishlist",
    ),


    # AJAX endpoint: lightweight car info for modals
    # URL: /cars/<uuid:pk>/modal-info/
    # Returns JSON with price, fee, photos, etc.

    path(
        "<uuid:pk>/modal-info/",
        views.car_modal_info,
        name="car_modal_info",
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# NEW CAR DETAIL URLS
# ─────────────────────────────────────────────────────────────────────────────

urlpatterns += [
    # ── Wishlist (AJAX + fallback POST) ───────────────────────────
    path(
        "cars/<uuid:pk>/wishlist/",
        views.toggle_wishlist,
        name="toggle_wishlist",
    ),

    # ── Reviews ───────────────────────────────────────────────────
    path(
        "cars/<uuid:pk>/review/",
        views.car_review,
        name="car_review",
    ),

    # ── Comments ──────────────────────────────────────────────────
    path(
        "cars/<uuid:pk>/comment/",
        views.car_comment,
        name="car_comment",
    ),

    # ── Booking ───────────────────────────────────────────────────
    path(
        "cars/<uuid:pk>/book/",
        views.car_booking,
        name="car_booking",
    ),
    path(
        "bookings/<uuid:pk>/",
        views.booking_detail,
        name="booking_detail",
    ),

    # ── Visit Scheduling ──────────────────────────────────────────
    path(
        "cars/<uuid:pk>/schedule/",
        views.car_schedule,
        name="car_schedule",
    ),
    path(
        "schedules/<uuid:pk>/",
        views.schedule_detail,
        name="schedule_detail",
    ),
    
    
 path("dashboard/",  views.dashboard,name="dashboard"),

    # Car management actions
    path("dashboard/car/<uuid:pk>/approve/",views.approve_car, name="approve_car"),
    path("dashboard/car/<uuid:pk>/reject/", views.reject_car, name="reject_car"),
    path("dashboard/car/<uuid:pk>/delete/",views.delete_car, name="delete_car"),
    path("dashboard/car/<uuid:pk>/status/", views.update_car_status,   name="update_car_status"),
    path("dashboard/car/<uuid:pk>/return/", views.return_car_to_platform, name="return_car_to_platform"),

    # Payment / refund actions
    path("dashboard/payment/<uuid:pk>/confirm/", views.confirm_payment_dashboard, name="confirm_payment_dashboard"),
    path("dashboard/refund/<uuid:pk>/approve/",views.approve_refund,name="approve_refund"),

    # Booking / visit actions
    path("dashboard/booking/<uuid:pk>/handle/",views.handle_booking, name="handle_booking"),
    path("dashboard/booking/<uuid:pk>/complete/",views.complete_booking, name="complete_booking"),
    path("dashboard/visit/<uuid:pk>/confirm/",views.confirm_visit, name="confirm_visit"),
    path("dashboard/visit/<uuid:pk>/reject/",views.sales_reject_visit, name="sales_reject_visit"),

    # Support ticket actions
    path("dashboard/ticket/<uuid:pk>/assign/", views.assign_ticket, name="assign_ticket"),
    path("dashboard/ticket/<uuid:pk>/reply/", views.reply_ticket,  name="reply_ticket"),
    path("dashboard/ticket/<uuid:pk>/resolve/", views.resolve_ticket, name="resolve_ticket"),
    path("dashboard/message/<uuid:pk>/reply/", views.reply_site_message, name="reply_site_message"),

    # User management actions
    path("dashboard/user/<uuid:pk>/deactivate/", views.deactivate_user, name="deactivate_user"),
    path("dashboard/user/<uuid:pk>/activate/", views.activate_user, name="activate_user"),
    path("dashboard/user/<uuid:pk>/delete/",views.delete_user, name="delete_user"),
    path("dashboard/user/<uuid:pk>/reset-password/", views.reset_user_password, name="reset_user_password"),

    # Notifications
    path("notifications/",  views.notifications_list,  name="notifications_list"),
    path("notifications/<uuid:pk>/read/",views.mark_notification_read, name="mark_notification_read"),
    # Legacy cars page (redirect)
    path("market/",views.cars,  name="cars"),  
    path('services/', views.services, name='services'),  
    path('about/', views.about_us, name='about_us'),
    
    path('contact/', views.contact, name='contact'),
    path('admin/settings/', views.site_settings_view, name='site_settings'),
    path('admin/settings/remove-logo/', views.site_settings_remove_logo, name='site_settings_remove_logo'),
    path('admin/settings/remove-banner/', views.site_settings_remove_banner, name='site_settings_remove_banner'),
    
    path('manager-report-pdf/', views.manager_report_pdf, name='manager_report_pdf'),
    
    # WhatsApp webhook for incoming messages and status updates
    path('whatsapp/webhook/', whatsapp_webhook, name='whatsapp_webhook'),
]
