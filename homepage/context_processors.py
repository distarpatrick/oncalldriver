from .models import SiteSettings
from .models import Notification


def _media_url(field_file):
    if not field_file:
        return ""
    try:
        if field_file.name and field_file.storage.exists(field_file.name):
            return field_file.url
    except (OSError, ValueError):
        return ""
    return ""


def site_branding(request):
    site_settings = SiteSettings.objects.first()
    notifications = []
    unread_count = 0
    if getattr(request, "user", None) and request.user.is_authenticated:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        notifications = list(
            Notification.objects.filter(user=request.user)
            .order_by("-created_at")[:6]
        )
    return {
        "site": site_settings,
        "site_name": site_settings.site_name if site_settings else "On Call Driver",
        "site_logo": _media_url(site_settings.site_logo) if site_settings else "",
        "notification_items": notifications,
        "unread_notification_count": unread_count,
    }
