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
from .models import CartItem, Order, OrderItem, WishlistItem, cart_total


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


@login_required
def cart(request):
    """The signed-in user's cart, with the total to pay."""
    items = CartItem.objects.filter(student=request.user).select_related(
        "course__category", "course__instructor"
    )
    return render(
        request,
        "payments/cart.html",
        {"items": items, "total": cart_total(request.user)},
    )


@login_required
def cart_add(request, course_pk):
    """Put a paid course in the cart.

    Free courses never go in a cart — they enrol directly. A course
    the student already owns cannot be bought again.
    """
    course = get_object_or_404(
        Course, pk=course_pk, status=Course.Status.PUBLISHED
    )
    if request.method == "POST":
        if course.is_free:
            messages.info(
                request, "This course is free — enrol on it directly."
            )
        elif is_enrolled(request.user, course):
            messages.info(request, "You already own this course.")
        else:
            item, created = CartItem.objects.get_or_create(
                student=request.user, course=course
            )
            if created:
                messages.success(
                    request, f"“{course.title}” has been added to your cart."
                )
            else:
                messages.info(request, "That course is already in your cart.")
    return redirect("courses:detail", pk=course.pk)


@login_required
def cart_remove(request, course_pk):
    """Take a course out of the cart."""
    course = get_object_or_404(Course, pk=course_pk)
    if request.method == "POST":
        CartItem.objects.filter(student=request.user, course=course).delete()
        messages.success(
            request, f"“{course.title}” has been removed from your cart."
        )
    return redirect("payments:cart")


@login_required
def checkout_cart(request):
    """Buy everything in the cart through the simulated checkout.

    The page shows the cart and its total, takes card details that
    are never stored, and on confirmation creates one order for the
    whole cart, enrols the student on every course, and empties the
    cart. Coupons are applied here in a later step.
    """
    items = CartItem.objects.filter(student=request.user).select_related(
        "course"
    )
    total = cart_total(request.user)
    if not items.exists():
        messages.info(request, "Your cart is empty.")
        return redirect("payments:cart")
    if request.method == "POST":
        form = SimulatedCheckoutForm(request.POST)
        if form.is_valid():
            order = Order.objects.create(student=request.user, total=total)
            for item in items:
                OrderItem.objects.create(
                    order=order, course=item.course, price=item.course.price
                )
                Enrollment.objects.get_or_create(
                    student=request.user, course=item.course
                )
            items.delete()
            messages.success(
                request,
                f"Payment complete — you are now enrolled on {order.items.count()} course(s).",
            )
            return redirect("learning:student_dashboard")
    else:
        form = SimulatedCheckoutForm()
    return render(
        request,
        "payments/checkout_cart.html",
        {"form": form, "items": items, "total": total},
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
