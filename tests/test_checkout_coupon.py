"""Tests for checkout with a coupon applied."""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.learning.models import Enrollment
from apps.payments.models import CartItem, Coupon, Order
from tests.helpers import login_as, make_course, make_user
from tests.test_coupons import make_coupon
from tests.test_paid_enrolment import GOOD_CARD


class CheckoutCouponTests(TestCase):
    def setUp(self):
        self.student = make_user()
        self.course = make_course(price=100, title="Django Pro")
        self.other = make_course(price=50, title="Flask in a Weekend")
        login_as(self.client, self.student)

    def add_to_cart(self, course):
        CartItem.objects.create(student=self.student, course=course)

    def test_site_wide_coupon_discounts_the_whole_cart(self):
        self.add_to_cart(self.course)
        self.add_to_cart(self.other)
        coupon = make_coupon(code="LEARN20", percent=20)
        response = self.client.post(
            reverse("payments:apply_coupon"),
            {"code": "learn20", "next": reverse("payments:checkout_cart")},
        )
        self.assertRedirects(response, reverse("payments:checkout_cart"))
        response = self.client.post(reverse("payments:checkout_cart"), GOOD_CARD)
        self.assertRedirects(response, reverse("learning:student_dashboard"))
        order = Order.objects.get(student=self.student)
        self.assertEqual(order.coupon, coupon)
        self.assertEqual(order.discount_amount, Decimal("30.00"))
        self.assertEqual(order.total, Decimal("120.00"))
        prices = sorted(
            order.items.values_list("price", flat=True), reverse=True
        )
        self.assertEqual(prices, [Decimal("80.00"), Decimal("40.00")])

    def test_checkout_page_shows_the_discount(self):
        self.add_to_cart(self.course)
        make_coupon(code="LEARN20", percent=20)
        self.client.post(
            reverse("payments:apply_coupon"),
            {"code": "LEARN20", "next": reverse("payments:checkout_cart")},
        )
        response = self.client.get(reverse("payments:checkout_cart"))
        self.assertContains(response, "LEARN20")
        self.assertContains(response, "20.00")
        self.assertContains(response, "80.00")

    def test_one_course_coupon_discounts_only_its_course(self):
        self.add_to_cart(self.course)
        self.add_to_cart(self.other)
        make_coupon(
            code="DJANGO50", percent=50, scope=Coupon.Scope.COURSE, course=self.course
        )
        self.client.post(
            reverse("payments:apply_coupon"),
            {"code": "DJANGO50", "next": reverse("payments:checkout_cart")},
        )
        self.client.post(reverse("payments:checkout_cart"), GOOD_CARD)
        order = Order.objects.get(student=self.student)
        self.assertEqual(order.discount_amount, Decimal("50.00"))
        self.assertEqual(order.total, Decimal("100.00"))

    def test_unknown_code_is_rejected(self):
        self.add_to_cart(self.course)
        # No assertRedirects here: following the redirect would
        # consume the error message before we can check for it.
        self.client.post(
            reverse("payments:apply_coupon"),
            {"code": "NOPE", "next": reverse("payments:checkout_cart")},
        )
        response = self.client.get(reverse("payments:checkout_cart"))
        self.assertNotContains(response, "Discount (NOPE)")
        self.assertContains(response, "does not exist")

    def test_expired_code_is_rejected(self):
        self.add_to_cart(self.course)
        now = timezone.now()
        Coupon.objects.create(
            code="OLD",
            percent=20,
            valid_from=now - timedelta(days=30),
            valid_until=now - timedelta(days=1),
        )
        self.client.post(
            reverse("payments:apply_coupon"),
            {"code": "OLD", "next": reverse("payments:checkout_cart")},
        )
        response = self.client.get(reverse("payments:checkout_cart"))
        self.assertContains(response, "expired or is not active")

    def test_code_for_a_course_not_in_the_cart_is_rejected(self):
        self.add_to_cart(self.other)
        make_coupon(
            code="DJANGO50", percent=50, scope=Coupon.Scope.COURSE, course=self.course
        )
        self.client.post(
            reverse("payments:apply_coupon"),
            {"code": "DJANGO50", "next": reverse("payments:checkout_cart")},
        )
        response = self.client.get(reverse("payments:checkout_cart"))
        self.assertContains(response, "does not apply to anything in your cart")

    def test_removing_the_coupon_restores_the_full_price(self):
        self.add_to_cart(self.course)
        make_coupon(code="LEARN20", percent=20)
        self.client.post(
            reverse("payments:apply_coupon"),
            {"code": "LEARN20", "next": reverse("payments:checkout_cart")},
        )
        self.client.post(
            reverse("payments:remove_coupon"),
            {"next": reverse("payments:checkout_cart")},
        )
        response = self.client.get(reverse("payments:checkout_cart"))
        # The old "applied" flash message may still show; what must
        # be gone is the discount itself.
        self.assertNotContains(response, "Discount (LEARN20)")
        self.assertContains(response, "100.00")

    def test_coupon_is_cleared_after_a_successful_order(self):
        self.add_to_cart(self.course)
        make_coupon(code="LEARN20", percent=20)
        self.client.post(
            reverse("payments:apply_coupon"),
            {"code": "LEARN20", "next": reverse("payments:checkout_cart")},
        )
        self.client.post(reverse("payments:checkout_cart"), GOOD_CARD)
        self.assertNotIn("coupon_id", self.client.session)

    def test_single_course_checkout_with_a_coupon(self):
        make_coupon(code="LEARN20", percent=20)
        url = reverse("payments:checkout_course", args=[self.course.pk])
        self.client.post(
            reverse("payments:apply_coupon"), {"code": "LEARN20", "next": url}
        )
        response = self.client.post(url, GOOD_CARD)
        self.assertRedirects(
            response, reverse("courses:detail", args=[self.course.pk])
        )
        order = Order.objects.get(student=self.student)
        self.assertEqual(order.total, Decimal("80.00"))
        self.assertEqual(order.discount_amount, Decimal("20.00"))
        self.assertTrue(
            Enrollment.objects.filter(
                student=self.student, course=self.course
            ).exists()
        )
