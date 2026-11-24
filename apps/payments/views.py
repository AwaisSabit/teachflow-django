"""Payment views: wishlist, cart and the simulated checkout.

The checkout is simulated: the student enters card details that are
checked for shape only and never stored, and the order completes
straight away. There is no real payment gateway here.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.courses.models import Course
from apps.learning.models import Enrollment, is_enrolled

from .forms import SimulatedCheckoutForm
from .models import Order, OrderItem, WishlistItem


@login_required
def wishlist(request):
    """The signed-in user's saved courses."""
    items = WishlistItem.objects.filter(student=request.user).select_related(
        "course__category", "course__instructor"
    )
    return render(request, "payments/wishlist.html", {"items": items})


@login_required
def wishlist_add(request, course_pk):
    """Save a published course to the wishlist."""
    course = get_object_or_404(
        Course, pk=course_pk, status=Course.Status.PUBLISHED
    )
    if request.method == "POST":
        item, created = WishlistItem.objects.get_or_create(
            student=request.user, course=course
        )
        if created:
            messages.success(
                request, f"“{course.title}” has been added to your wishlist."
            )
        else:
            messages.info(request, "That course is already on your wishlist.")
    return redirect("courses:detail", pk=course.pk)


@login_required
def wishlist_remove(request, course_pk):
    """Take a course off the wishlist."""
    course = get_object_or_404(Course, pk=course_pk)
    if request.method == "POST":
        deleted, _ = WishlistItem.objects.filter(
            student=request.user, course=course
        ).delete()
        if deleted:
            messages.success(
                request, f"“{course.title}” has been removed from your wishlist."
            )
    return redirect("payments:wishlist")


def cart(request):
    """Placeholder cart page."""
    return render(
        request,
        "coming_soon.html",
        {"title": "My cart", "message": "Your cart is coming soon."},
    )


@login_required
def checkout_course(request, course_pk):
    """Buy one paid course through the simulated checkout.

    The page shows the course and its price, takes card details that
    are never stored, and on confirmation creates the order and the
    enrolment. A free course never reaches this page — it enrols
    directly.
    """
    course = get_object_or_404(
        Course, pk=course_pk, status=Course.Status.PUBLISHED
    )
    if course.is_free:
        messages.info(request, "This course is free — enrol on it directly.")
        return redirect("courses:detail", pk=course.pk)
    if is_enrolled(request.user, course):
        messages.info(request, "You are already enrolled on this course.")
        return redirect("courses:detail", pk=course.pk)
    if request.method == "POST":
        form = SimulatedCheckoutForm(request.POST)
        if form.is_valid():
            order = Order.objects.create(student=request.user, total=course.price)
            OrderItem.objects.create(
                order=order, course=course, price=course.price
            )
            Enrollment.objects.get_or_create(
                student=request.user, course=course
            )
            messages.success(
                request,
                f"Payment complete — you are now enrolled on “{course.title}”.",
            )
            return redirect("courses:detail", pk=course.pk)
    else:
        form = SimulatedCheckoutForm()
    return render(
        request,
        "payments/checkout.html",
        {"form": form, "course": course},
    )
