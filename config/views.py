"""Home and health-check views for TeachFlow."""
from django.http import JsonResponse
from django.shortcuts import render


def home(request):
    """Landing page: what TeachFlow does and how to reach each part."""
    return render(request, "home.html")


def health(request):
    """Simple health endpoint used by the smoke test (and later by monitoring)."""
    return JsonResponse({"status": "ok", "app": "teachflow"})
