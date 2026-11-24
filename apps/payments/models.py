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
