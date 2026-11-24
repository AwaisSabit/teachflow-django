"""Learning views: enrolment, dashboards and progress.

Enrolment is the front door to learning: a free course enrols with
one click; a paid course goes through the cart and checkout instead.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.courses.models import Course

from .models import Enrollment


@login_required
def enrol(request, course_pk):
    """Enrol the signed-in user on a free course.

    A free course enrols with one click and never asks for payment.
    A paid course cannot be enrolled on directly — it goes through
    the cart and the simulated checkout, which create the enrolment
    when the order completes.
    """
    course = get_object_or_404(
        Course, pk=course_pk, status=Course.Status.PUBLISHED
    )
    if request.method != "POST":
        return redirect("courses:detail", pk=course.pk)
    if not course.is_free:
        messages.info(
            request,
            "This is a paid course — add it to your cart to buy it.",
        )
        return redirect("courses:detail", pk=course.pk)
    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user, course=course
    )
    if created:
        messages.success(request, f"You are now enrolled on “{course.title}”.")
    else:
        messages.info(request, "You are already enrolled on this course.")
    return redirect("courses:detail", pk=course.pk)


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
