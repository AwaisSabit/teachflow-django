"""Payment views: wishlist, cart and the simulated checkout.

The checkout is simulated: the student enters card details that are
checked for shape only and never stored, and the order completes
straight away. There is no real payment gateway here.
"""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.courses.models import Course
from apps.learning.models import Enrollment, is_enrolled

from .forms import CouponForm, SimulatedCheckoutForm
from .models import CartItem, Coupon, Order, OrderItem, WishlistItem, cart_total


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
    if not items.exists():
        messages.info(request, "Your cart is empty.")
        return redirect("payments:cart")
    coupon = coupon_from_session(request)
    per_item_discount, discount = discount_for_items(items, coupon)
    subtotal = cart_total(request.user)
    total = subtotal - discount
    if request.method == "POST":
        form = SimulatedCheckoutForm(request.POST)
        if form.is_valid():
            order = Order.objects.create(
                student=request.user,
                total=total,
                coupon=coupon,
                discount_amount=discount,
            )
            for item in items:
                paid_price = item.course.price - per_item_discount.get(
                    item.pk, 0
                )
                OrderItem.objects.create(
                    order=order, course=item.course, price=paid_price
                )
                Enrollment.objects.get_or_create(
                    student=request.user, course=item.course
                )
            items.delete()
            request.session.pop("coupon_id", None)
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
        {
            "form": form,
            "coupon_form": CouponForm(),
            "coupon": coupon,
            "items": items,
            "per_item_discount": per_item_discount,
            "discount": discount,
            "subtotal": subtotal,
            "total": total,
        },
    )


def coupon_from_session(request):
    """The coupon the student applied at checkout, if it is still valid."""
    coupon_id = request.session.get("coupon_id")
    if not coupon_id:
        return None
    try:
        coupon = Coupon.objects.get(pk=coupon_id)
    except Coupon.DoesNotExist:
        return None
    if not coupon.is_valid_now():
        return None
    return coupon


def discount_for_items(items, coupon):
    """How much a coupon takes off these cart items, per item.

    A site-wide coupon discounts every item; a one-course coupon
    discounts only its own course. Returns (per-item discounts, total).
    """
    if coupon is None:
        return {}, 0
    from decimal import Decimal

    per_item = {}
    total_discount = Decimal("0.00")
    for item in items:
        if coupon.applies_to(item.course):
            discount = coupon.discount_for(item.course.price)
        else:
            discount = Decimal("0.00")
        per_item[item.pk] = discount
        total_discount += discount
    return per_item, total_discount


@login_required
def apply_coupon(request):
    """Apply a discount code, so checkout shows the discount.

    The code must exist and be inside its dates. When the cart has
    courses, the code must also apply to at least one of them — a
    one-course code for a course that is not in the cart is rejected
    instead of sitting there doing nothing. The form carries a `next`
    field, so a code typed on the single-course checkout returns
    there instead of to the cart.
    """
    next_url = request.POST.get("next") or reverse("payments:checkout_cart")
    if request.method == "POST":
        form = CouponForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"].strip().upper()
            coupon = Coupon.objects.filter(code__iexact=code).first()
            if coupon is None:
                messages.error(request, "That discount code does not exist.")
            elif not coupon.is_valid_now():
                messages.error(
                    request, "That discount code has expired or is not active."
                )
            else:
                cart_courses = [
                    item.course
                    for item in CartItem.objects.filter(
                        student=request.user
                    ).select_related("course")
                ]
                if cart_courses and not any(
                    coupon.applies_to(course) for course in cart_courses
                ):
                    messages.error(
                        request,
                        "That discount code does not apply to anything in your cart.",
                    )
                else:
                    request.session["coupon_id"] = coupon.pk
                    messages.success(
                        request,
                        f"Discount code {coupon.code} applied — {coupon.percent}% off.",
                    )
    return redirect(next_url)


@login_required
def remove_coupon(request):
    """Take the discount code off the checkout."""
    next_url = request.POST.get("next") or reverse("payments:checkout_cart")
    if request.method == "POST":
        request.session.pop("coupon_id", None)
        messages.info(request, "Discount code removed.")
    return redirect(next_url)


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
    coupon = coupon_from_session(request)
    discount = Decimal("0.00")
    if coupon is not None and coupon.applies_to(course):
        discount = coupon.discount_for(course.price)
    elif coupon is not None:
        coupon = None
    total = course.price - discount
    if request.method == "POST":
        form = SimulatedCheckoutForm(request.POST)
        if form.is_valid():
            order = Order.objects.create(
                student=request.user,
                total=total,
                coupon=coupon,
                discount_amount=discount,
            )
            OrderItem.objects.create(
                order=order, course=course, price=total
            )
            Enrollment.objects.get_or_create(
                student=request.user, course=course
            )
            request.session.pop("coupon_id", None)
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
        {
            "form": form,
            "coupon_form": CouponForm(),
            "coupon": coupon,
            "course": course,
            "discount": discount,
            "total": total,
        },
    )
