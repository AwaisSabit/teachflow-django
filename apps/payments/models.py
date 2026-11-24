"""Payment models: orders.

TeachFlow has no real payment gateway. A checkout is simulated: the
student enters card details that are checked for shape only and
never stored, and the order is marked completed straight away. The
order is the record of what was bought, at what price, and when.
"""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Order(models.Model):
    """A completed simulated purchase by one student."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon = models.ForeignKey(
        "Coupon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        help_text="The coupon used at checkout, if any.",
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="How much the coupon took off the total.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Sequential order numbers, one per student purchase.
            last = Order.objects.order_by("-id").values_list("id", flat=True).first()
            self.order_number = f"TF-{(last or 0) + 1:06d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_number} by {self.student.username}"


class OrderItem(models.Model):
    """One course inside an order, at the price paid for it."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items"
    )
    course = models.ForeignKey(
        "courses.Course", on_delete=models.PROTECT, related_name="order_items"
    )
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.course.title} in {self.order.order_number}"


class WishlistItem(models.Model):
    """A course a student saved to buy or take later."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, related_name="wishlisted_by"
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.student.username} saved {self.course.title}"


class CartItem(models.Model):
    """A paid course a student put in the cart, waiting for checkout."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, related_name="in_carts"
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.student.username} has {self.course.title} in the cart"


def cart_total(student):
    """What the student's cart costs, in total."""
    from django.db.models import Sum

    total = CartItem.objects.filter(student=student).aggregate(
        Sum("course__price")
    )["course__price__sum"]
    return total or 0


class Coupon(models.Model):
    """A percentage discount code.

    A coupon is site-wide, or tied to one course. It only works while
    it is active and inside its dates. The discount is a percentage
    of the price it applies to — never more than the price itself.
    """

    class Scope(models.TextChoices):
        SITE = "site", "Site-wide"
        COURSE = "course", "One course"

    code = models.CharField(
        max_length=30,
        unique=True,
        help_text="The code the student types at checkout, such as LEARN20.",
    )
    percent = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1, "A discount is at least 1 percent."),
            MaxValueValidator(90, "A discount is at most 90 percent."),
        ],
        help_text="The percentage taken off the price.",
    )
    scope = models.CharField(
        max_length=20, choices=Scope.choices, default=Scope.SITE
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="coupons",
        help_text="The one course this coupon works for, when the scope is one course.",
    )
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.valid_until <= self.valid_from:
            raise ValidationError("The coupon must end after it starts.")
        if self.scope == self.Scope.COURSE and self.course is None:
            raise ValidationError(
                "A one-course coupon needs a course to work for."
            )
        if self.scope == self.Scope.SITE and self.course is not None:
            raise ValidationError("A site-wide coupon has no single course.")

    def is_valid_now(self):
        """True when the coupon is switched on and inside its dates."""
        from django.utils import timezone

        now = timezone.now()
        return self.active and self.valid_from <= now <= self.valid_until

    def applies_to(self, course):
        """True when this coupon may discount this course, right now."""
        if not self.is_valid_now():
            return False
        if self.scope == self.Scope.SITE:
            return True
        return self.course_id == course.pk

    def discount_for(self, amount):
        """The money taken off this amount, rounded to two places."""
        from decimal import Decimal, ROUND_HALF_UP

        discount = (Decimal(amount) * self.percent / 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return min(discount, Decimal(amount))

    def __str__(self):
        return f"{self.code} — {self.percent}% off"
