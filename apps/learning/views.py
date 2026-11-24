"""Learning views: student and instructor dashboards.

Placeholders until the dashboard commits land.
"""
from django.shortcuts import render


def student_dashboard(request):
    """Placeholder student dashboard."""
    return render(
        request,
        "coming_soon.html",
        {"title": "My learning", "message": "Your learning dashboard is coming soon."},
    )


def instructor_dashboard(request):
    """Placeholder instructor dashboard."""
    return render(
        request,
        "coming_soon.html",
        {"title": "Teach", "message": "Your instructor dashboard is coming soon."},
    )
