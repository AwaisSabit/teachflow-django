"""Tests for the course publishing workflow."""
from django.test import TestCase
from django.urls import reverse

from apps.courses.models import Course
from tests.helpers import login_as, make_course, make_instructor

MY_COURSES_URL = reverse("courses:my_courses")


class PublishingTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.other = make_instructor(username="other-teacher")
        self.course = make_course(
            instructor=self.instructor, status=Course.Status.DRAFT
        )
        login_as(self.client, self.instructor)

    def _post(self, name, course):
        return self.client.post(reverse(f"courses:{name}", args=[course.pk]))

    def test_submit_moves_draft_to_submitted(self):
        response = self._post("submit", self.course)
        self.assertRedirects(response, MY_COURSES_URL)
        self.course.refresh_from_db()
        self.assertEqual(self.course.status, Course.Status.SUBMITTED)

    def test_publish_moves_submitted_to_published(self):
        self.course.status = Course.Status.SUBMITTED
        self.course.save()
        response = self._post("publish", self.course)
        self.assertRedirects(response, MY_COURSES_URL)
        self.course.refresh_from_db()
        self.assertEqual(self.course.status, Course.Status.PUBLISHED)

    def test_publish_refuses_a_draft(self):
        self._post("publish", self.course)
        self.course.refresh_from_db()
        self.assertEqual(self.course.status, Course.Status.DRAFT)

    def test_submit_refuses_a_published_course(self):
        self.course.status = Course.Status.PUBLISHED
        self.course.save()
        self._post("submit", self.course)
        self.course.refresh_from_db()
        self.assertEqual(self.course.status, Course.Status.PUBLISHED)

    def test_withdraw_returns_a_published_course_to_draft(self):
        self.course.status = Course.Status.PUBLISHED
        self.course.save()
        self._post("withdraw", self.course)
        self.course.refresh_from_db()
        self.assertEqual(self.course.status, Course.Status.DRAFT)

    def test_withdraw_refuses_a_draft(self):
        self._post("withdraw", self.course)
        self.course.refresh_from_db()
        self.assertEqual(self.course.status, Course.Status.DRAFT)

    def test_another_instructor_cannot_submit_my_course(self):
        login_as(self.client, self.other)
        response = self._post("submit", self.course)
        self.assertEqual(response.status_code, 404)
        self.course.refresh_from_db()
        self.assertEqual(self.course.status, Course.Status.DRAFT)

    def test_student_cannot_publish(self):
        from tests.helpers import make_user

        login_as(self.client, make_user(username="student-x"))
        response = self._post("publish", self.course)
        self.assertEqual(response.status_code, 403)

    def test_category_page_shows_only_published_courses(self):
        published = make_course(
            instructor=self.instructor, title="Published One"
        )
        make_course(
            instructor=self.instructor,
            title="Draft One",
            status=Course.Status.DRAFT,
        )
        response = self.client.get(
            reverse("courses:category", args=[published.category.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published One")
        self.assertNotContains(response, "Draft One")

    def test_get_does_not_change_status(self):
        response = self.client.get(
            reverse("courses:submit", args=[self.course.pk])
        )
        self.assertRedirects(response, MY_COURSES_URL)
        self.course.refresh_from_db()
        self.assertEqual(self.course.status, Course.Status.DRAFT)
