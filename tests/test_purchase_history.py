"""Tests for the purchase history page."""
from django.test import TestCase
from django.urls import reverse

from apps.payments.models import Order, OrderItem
from tests.helpers import login_as, make_course, make_user
from tests.test_coupons import make_coupon


class PurchaseHistoryTests(TestCase):
    def setUp(self):
        self.student = make_user()
        self.course = make_course(price=100, title="Django Pro")
        login_as(self.client, self.student)

    def make_order(self, student=None, **kwargs):
        order = Order.objects.create(
            student=student or self.student, **kwargs
        )
        OrderItem.objects.create(
            order=order, course=self.course, price=kwargs.get("total", 100)
        )
        return order

    def test_history_lists_my_orders(self):
        self.make_order(total=100)
        response = self.client.get(reverse("payments:history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TF-000001")
        self.assertContains(response, "Django Pro")
        self.assertContains(response, "100")

    def test_history_shows_coupon_and_discount(self):
        coupon = make_coupon(code="LEARN20", percent=20)
        self.make_order(total=80, coupon=coupon, discount_amount=20)
        response = self.client.get(reverse("payments:history"))
        self.assertContains(response, "LEARN20")
        self.assertContains(response, "20")

    def test_history_is_per_user(self):
        self.make_order(total=100)
        login_as(self.client, make_user(username="someone-else"))
        response = self.client.get(reverse("payments:history"))
        self.assertNotContains(response, "TF-000001")
        self.assertContains(response, "not bought any courses yet")

    def test_history_empty_state(self):
        response = self.client.get(reverse("payments:history"))
        self.assertContains(response, "not bought any courses yet")

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("payments:history"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
