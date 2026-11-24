"""Payment models: orders.

TeachFlow has no real payment gateway. A checkout is simulated: the
student enters card details that are checked for shape only and
never stored, and the order is marked completed straight away. The
order is the record of what was bought, at what price, and when.
"""
from django.conf import settings
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
    created_at = models.DateTimeField(auto_now_add=True)

    # Coupons land later: a coupon field and a discount amount are
    # added to this model when checkout learns about coupons.

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
