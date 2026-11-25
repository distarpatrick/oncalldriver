"""URL configuration for the On Call Driver project."""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

admin.site.site_header = "On Call Driver — Administration"
admin.site.site_title = "On Call Driver Admin"
admin.site.index_title = "Control panel"

urlpatterns = [
    path('', include('homepage.urls')),
    path('pay/', include('payment.urls')),
    # Django built-in auth views (password reset, login/out helpers)
    path('accounts/', include('django.contrib.auth.urls')),
    path(settings.ADMIN_URL, admin.site.urls),
]

if settings.SERVE_MEDIA:
    # User uploads (car photos, receipts). For larger deployments move media
    # to object storage (S3/Cloudinary) and set DJANGO_SERVE_MEDIA=false.
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
