"""Tests for instructor preview mode."""
from django.test import TestCase
from django.urls import reverse

from apps.courses.models import Course
from tests.helpers import login_as, make_course, make_instructor, make_user
from tests.test_lessons import make_lesson, make_section


class CoursePreviewTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.course = make_course(instructor=self.instructor)
        self.section = make_section(course=self.course)
        self.lesson = make_lesson(self.section)
        login_as(self.client, self.instructor)

    def preview_url(self, course=None):
        return reverse(
            "courses:preview", args=[(course or self.course).pk]
        )

    def test_instructor_can_preview_a_published_course(self):
        response = self.client.get(self.preview_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "previewing this course as a student")
        self.assertContains(response, "Python for Beginners")

    def test_instructor_can_preview_a_draft_course(self):
        draft = make_course(
            instructor=self.instructor,
            title="Draft Course",
            status=Course.Status.DRAFT,
        )
        response = self.client.get(self.preview_url(draft))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Draft Course")

    def test_preview_hides_instructor_tools(self):
        response = self.client.get(self.preview_url())
        self.assertNotContains(response, "Add a section")
        self.assertNotContains(response, "Add a lesson")
        self.assertNotContains(response, "Preview as a student")
        self.assertContains(response, "enrolment is disabled")

    def test_preview_does_not_offer_enrolment_or_wishlist(self):
        response = self.client.get(self.preview_url())
        self.assertNotContains(response, "Enrol for free")
        self.assertNotContains(response, "Buy this course")
        self.assertNotContains(response, "Save to wishlist")

    def test_normal_view_still_shows_the_preview_button(self):
        response = self.client.get(
            reverse("courses:detail", args=[self.course.pk])
        )
        self.assertContains(response, "Preview as a student")
        self.assertContains(response, "Add a section")

    def test_other_instructor_cannot_preview_my_course(self):
        login_as(self.client, make_instructor(username="other-teacher"))
        response = self.client.get(self.preview_url())
        self.assertEqual(response.status_code, 404)

    def test_student_cannot_preview(self):
        login_as(self.client, make_user(username="plain-student"))
        response = self.client.get(self.preview_url())
        self.assertEqual(response.status_code, 403)
