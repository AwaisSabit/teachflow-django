"""TeachFlow URL configuration."""
from django.contrib import admin
from django.urls import include, path

from config.views import health, home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("health/", health, name="health"),
    path("accounts/", include("apps.accounts.urls")),
    path("courses/", include("apps.courses.urls")),
    path("learning/", include("apps.learning.urls")),
    path("payments/", include("apps.payments.urls")),
]
