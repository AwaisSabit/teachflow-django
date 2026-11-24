"""Course browsing views.

Learners browse by category. The browse page lists every category;
a category page shows the category and, once courses exist, the
published courses inside it.
"""
from django.shortcuts import get_object_or_404, render

from .models import Category


def browse(request):
    """List every category, so learners can pick a topic to explore."""
    categories = Category.objects.all()
    return render(request, "courses/browse.html", {"categories": categories})


def category_detail(request, slug):
    """One category: its description and its published courses.

    The Course model lands in the next commit, so for now the page
    shows the category and an honest empty state.
    """
    category = get_object_or_404(Category, slug=slug)
    courses = []
    return render(
        request,
        "courses/category_detail.html",
        {"category": category, "courses": courses},
    )
