"""Tests for the course detail page."""
from django.test import TestCase
from django.urls import reverse

from apps.courses.models import Course
from tests.helpers import login_as, make_course, make_instructor, make_user


class CourseDetailTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor(
            display_name="Bilal Ahmed",
            bio="Python teacher with ten years of experience.",
        )
        self.course = make_course(
            instructor=self.instructor,
            title="Django for Beginners",
            subtitle="Build your first web app.",
            description="A friendly first course in Django.",
            what_you_will_learn="Build a Django app\nUse the admin",
            requirements="A computer with Python installed",
        )

    def test_published_course_detail_shows_everything(self):
        response = self.client.get(
            reverse("courses:detail", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django for Beginners")
        self.assertContains(response, "Build your first web app.")
        self.assertContains(response, "A friendly first course in Django.")
        self.assertContains(response, "Build a Django app")
        self.assertContains(response, "Use the admin")
        self.assertContains(response, "A computer with Python installed")
        self.assertContains(response, "Bilal Ahmed")
        self.assertContains(response, "ten years of experience")
        self.assertContains(response, "Free")

    def test_detail_shows_price_for_paid_courses(self):
        paid = make_course(price=49.99, title="Django Pro")
        response = self.client.get(reverse("courses:detail", args=[paid.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "49.99")

    def test_draft_is_404_for_anonymous_visitors(self):
        draft = make_course(status=Course.Status.DRAFT, title="Draft Course")
        response = self.client.get(reverse("courses:detail", args=[draft.pk]))
        self.assertEqual(response.status_code, 404)

    def test_draft_is_404_for_other_users(self):
        draft = make_course(status=Course.Status.DRAFT, title="Draft Course")
        login_as(self.client, make_user(username="curious"))
        response = self.client.get(reverse("courses:detail", args=[draft.pk]))
        self.assertEqual(response.status_code, 404)

    def test_owner_can_view_their_own_draft(self):
        draft = make_course(
            instructor=self.instructor,
            status=Course.Status.DRAFT,
            title="My Draft",
        )
        login_as(self.client, self.instructor)
        response = self.client.get(reverse("courses:detail", args=[draft.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Draft")

    def test_curriculum_empty_state_before_sections_exist(self):
        response = self.client.get(
            reverse("courses:detail", args=[self.course.pk])
        )
        self.assertContains(response, "curriculum for this course is not ready yet")

    def test_unknown_course_is_404(self):
        response = self.client.get(reverse("courses:detail", args=[99999]))
        self.assertEqual(response.status_code, 404)
