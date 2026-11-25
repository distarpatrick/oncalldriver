from django.urls import path

from . import views

app_name = "payment"

urlpatterns = [
    path("<uuid:pk>/", views.checkout, name="checkout"),
    path("<uuid:pk>/start/", views.start, name="start"),
    path("<uuid:pk>/status/", views.status, name="status"),
    path("<uuid:pk>/proof/", views.proof, name="proof"),
    path("callback/mtn/<str:token>/", views.mtn_callback, name="mtn_callback"),
    path("callback/airtel/<str:token>/", views.airtel_callback, name="airtel_callback"),
]
