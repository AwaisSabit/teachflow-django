"""Tests for the shopping cart."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.learning.models import Enrollment
from apps.payments.models import CartItem, Order, cart_total
from tests.helpers import login_as, make_course, make_user
from tests.test_paid_enrolment import GOOD_CARD


class CartTests(TestCase):
    def setUp(self):
        self.student = make_user()
        self.course = make_course(price=49.99, title="Django Pro")
        self.other = make_course(price=19.99, title="Flask in a Weekend")
        login_as(self.client, self.student)

    def test_add_puts_a_paid_course_in_the_cart(self):
        response = self.client.post(
            reverse("payments:cart_add", args=[self.course.pk])
        )
        self.assertRedirects(
            response, reverse("courses:detail", args=[self.course.pk])
        )
        self.assertTrue(
            CartItem.objects.filter(
                student=self.student, course=self.course
            ).exists()
        )

    def test_adding_twice_keeps_one_item(self):
        url = reverse("payments:cart_add", args=[self.course.pk])
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(
            CartItem.objects.filter(
                student=self.student, course=self.course
            ).count(),
            1,
        )

    def test_free_course_cannot_go_in_the_cart(self):
        free = make_course(price=0, title="Free Course")
        self.client.post(reverse("payments:cart_add", args=[free.pk]))
        self.assertFalse(
            CartItem.objects.filter(student=self.student, course=free).exists()
        )

    def test_owned_course_cannot_go_in_the_cart(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        self.client.post(reverse("payments:cart_add", args=[self.course.pk]))
        self.assertFalse(
            CartItem.objects.filter(
                student=self.student, course=self.course
            ).exists()
        )

    def test_cart_page_shows_items_and_total(self):
        CartItem.objects.create(student=self.student, course=self.course)
        CartItem.objects.create(student=self.student, course=self.other)
        response = self.client.get(reverse("payments:cart"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django Pro")
        self.assertContains(response, "Flask in a Weekend")
        self.assertContains(response, "69.98")

    def test_cart_total_adds_prices(self):
        CartItem.objects.create(student=self.student, course=self.course)
        CartItem.objects.create(student=self.student, course=self.other)
        self.assertEqual(cart_total(self.student), Decimal("69.98"))
        self.assertEqual(cart_total(make_user(username="nobody")), Decimal("0"))

    def test_remove_takes_the_course_out(self):
        CartItem.objects.create(student=self.student, course=self.course)
        response = self.client.post(
            reverse("payments:cart_remove", args=[self.course.pk])
        )
        self.assertRedirects(response, reverse("payments:cart"))
        self.assertFalse(
            CartItem.objects.filter(
                student=self.student, course=self.course
            ).exists()
        )

    def test_cart_is_per_user(self):
        CartItem.objects.create(student=self.student, course=self.course)
        login_as(self.client, make_user(username="someone-else"))
        response = self.client.get(reverse("payments:cart"))
        self.assertNotContains(response, "Django Pro")

    def test_cart_checkout_creates_one_order_and_enrols(self):
        CartItem.objects.create(student=self.student, course=self.course)
        CartItem.objects.create(student=self.student, course=self.other)
        response = self.client.post(
            reverse("payments:checkout_cart"), GOOD_CARD
        )
        self.assertRedirects(
            response, reverse("learning:student_dashboard")
        )
        order = Order.objects.get(student=self.student)
        self.assertEqual(order.total, Decimal("69.98"))
        self.assertEqual(order.items.count(), 2)
        self.assertTrue(
            Enrollment.objects.filter(
                student=self.student, course=self.course
            ).exists()
        )
        self.assertTrue(
            Enrollment.objects.filter(
                student=self.student, course=self.other
            ).exists()
        )
        self.assertFalse(
            CartItem.objects.filter(student=self.student).exists()
        )

    def test_empty_cart_checkout_redirects_to_cart(self):
        response = self.client.get(reverse("payments:checkout_cart"))
        self.assertRedirects(response, reverse("payments:cart"))

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.post(
            reverse("payments:cart_add", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
