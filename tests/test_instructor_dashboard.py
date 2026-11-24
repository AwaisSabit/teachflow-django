"""Tests for the instructor dashboard."""
from django.test import TestCase
from django.urls import reverse

from apps.courses.models import Review
from apps.learning.models import Enrollment
from apps.payments.models import Order, OrderItem
from tests.helpers import login_as, make_course, make_instructor, make_user


class InstructorDashboardTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.course = make_course(instructor=self.instructor)
        self.student = make_user()
        self.other = make_user(username="second-student")
        login_as(self.client, self.instructor)

    def url(self):
        return reverse("learning:instructor_dashboard")

    def test_dashboard_shows_my_courses_and_counts(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        Enrollment.objects.create(student=self.other, course=self.course)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python for Beginners")
        self.assertContains(response, "Students")
        self.assertContains(response, "Enrolments")
        self.assertContains(response, "2")

    def test_dashboard_shows_average_rating(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        Review.objects.create(
            course=self.course, student=self.student, rating=5, comment="Great"
        )
        response = self.client.get(self.url())
        self.assertContains(response, "5.0 / 5")

    def test_dashboard_shows_earnings_from_orders(self):
        buyer = make_user(username="buyer")
        order = Order.objects.create(student=buyer, total=49.99)
        OrderItem.objects.create(
            order=order, course=self.course, price=49.99
        )
        response = self.client.get(self.url())
        self.assertContains(response, "49.99")

    def test_dashboard_only_shows_my_own_courses(self):
        make_course(title="Someone Else's Course")
        response = self.client.get(self.url())
        self.assertContains(response, "Python for Beginners")
        self.assertNotContains(response, "Someone Else's Course")

    def test_student_gets_a_403(self):
        login_as(self.client, make_user(username="plain-student"))
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 403)

    def test_empty_state(self):
        response = self.client.get(self.url())
        self.assertContains(response, "Python for Beginners")
        login_as(self.client, make_instructor(username="new-teacher"))
        response = self.client.get(self.url())
        self.assertContains(response, "no courses yet")
