"""Course browsing and detail views.

The browse page is a placeholder until the category browsing lands;
it is replaced by the real view in the categories commit.
"""
from django.shortcuts import render


def browse(request):
    """Placeholder browse page, replaced by the real course list."""
    return render(
        request,
        "coming_soon.html",
        {"title": "Browse courses", "message": "Course browsing is coming soon."},
    )
