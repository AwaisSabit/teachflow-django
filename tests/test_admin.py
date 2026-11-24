"""Tests for the admin customisation."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.courses.models import Course
from apps.learning.models import Enrollment
from apps.payments.models import Order
from tests.helpers import make_course, make_instructor, make_user

User = get_user_model()


class AdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="AdminPass123!",
        )
        self.client.force_login(self.admin)
        self.instructor = make_instructor()
        self.course = make_course(instructor=self.instructor)

    def test_course_changelist_loads_with_search_and_filters(self):
        url = reverse("admin:courses_course_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python for Beginners")
        response = self.client.get(url + "?q=Python")
        self.assertContains(response, "Python for Beginners")
        response = self.client.get(url + "?status=published")
        self.assertContains(response, "Python for Beginners")
        response = self.client.get(url + "?status=draft")
        self.assertNotContains(response, "Python for Beginners")

    def test_order_changelist_loads(self):
        Order.objects.create(student=make_user(), total=49.99)
        response = self.client.get(reverse("admin:payments_order_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TF-000001")

    def test_enrolment_changelist_shows_progress(self):
        student = make_user()
        Enrollment.objects.create(student=student, course=self.course)
        response = self.client.get(
            reverse("admin:learning_enrollment_changelist")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0%")

    def test_quiz_and_certificate_changelists_load(self):
        response = self.client.get(reverse("admin:learning_quiz_changelist"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("admin:learning_certificate_changelist")
        )
        self.assertEqual(response.status_code, 200)

    def test_lesson_and_review_changelists_load(self):
        response = self.client.get(reverse("admin:courses_lesson_changelist"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("admin:courses_review_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_coupon_changelist_loads(self):
        response = self.client.get(reverse("admin:payments_coupon_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_non_staff_cannot_open_the_admin(self):
        self.client.logout()
        self.client.force_login(make_user(username="plain"))
        response = self.client.get(reverse("admin:courses_course_changelist"))
        self.assertEqual(response.status_code, 302)
