"""Tests for paid enrolment through the simulated checkout."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.learning.models import Enrollment
from apps.payments.models import Order
from tests.helpers import login_as, make_course, make_user

GOOD_CARD = {
    "card_number": "4242 4242 4242 4242",
    "expiry": "12/29",
    "cvc": "123",
}


class SimulatedCheckoutTests(TestCase):
    def setUp(self):
        self.student = make_user()
        self.course = make_course(price=49.99, title="Django Pro")
        login_as(self.client, self.student)

    def checkout_url(self, course=None):
        return reverse(
            "payments:checkout_course", args=[(course or self.course).pk]
        )

    def test_checkout_page_loads_with_price(self):
        response = self.client.get(self.checkout_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django Pro")
        self.assertContains(response, "49.99")
        self.assertContains(response, "simulated checkout")

    def test_successful_checkout_creates_order_and_enrolment(self):
        response = self.client.post(self.checkout_url(), GOOD_CARD)
        self.assertRedirects(
            response, reverse("courses:detail", args=[self.course.pk])
        )
        order = Order.objects.get(student=self.student)
        self.assertEqual(order.total, Decimal("49.99"))
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().course, self.course)
        self.assertTrue(order.order_number.startswith("TF-"))
        self.assertTrue(
            Enrollment.objects.filter(
                student=self.student, course=self.course
            ).exists()
        )

    def test_order_numbers_are_sequential(self):
        self.client.post(self.checkout_url(), GOOD_CARD)
        other = make_course(price=19.99, title="Second Course")
        self.client.post(self.checkout_url(other), GOOD_CARD)
        numbers = list(
            Order.objects.order_by("id").values_list("order_number", flat=True)
        )
        self.assertEqual(numbers, ["TF-000001", "TF-000002"])

    def test_invalid_card_number_is_rejected(self):
        response = self.client.post(
            self.checkout_url(),
            {**GOOD_CARD, "card_number": "1234"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.filter(student=self.student).exists())
        self.assertFalse(
            Enrollment.objects.filter(
                student=self.student, course=self.course
            ).exists()
        )

    def test_invalid_expiry_is_rejected(self):
        response = self.client.post(
            self.checkout_url(), {**GOOD_CARD, "expiry": "13/29"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.filter(student=self.student).exists())

    def test_invalid_cvc_is_rejected(self):
        response = self.client.post(
            self.checkout_url(), {**GOOD_CARD, "cvc": "12"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.filter(student=self.student).exists())

    def test_card_details_are_never_stored(self):
        self.client.post(self.checkout_url(), GOOD_CARD)
        order = Order.objects.get(student=self.student)
        self.assertNotIn("4242", str(order.__dict__))

    def test_already_enrolled_student_is_sent_back(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        response = self.client.get(self.checkout_url())
        self.assertRedirects(
            response, reverse("courses:detail", args=[self.course.pk])
        )
        self.assertFalse(Order.objects.filter(student=self.student).exists())

    def test_free_course_checkout_redirects_to_detail(self):
        free = make_course(price=0, title="Free Course")
        response = self.client.get(self.checkout_url(free))
        self.assertRedirects(
            response, reverse("courses:detail", args=[free.pk])
        )

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(self.checkout_url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
