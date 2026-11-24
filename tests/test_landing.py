"""Tests for the polished course landing page."""
from django.test import TestCase
from django.urls import reverse

from tests.helpers import make_course
from tests.test_lessons import make_lesson, make_section


class LandingTests(TestCase):
    def setUp(self):
        self.course = make_course(
            what_you_will_learn="Build a Django app\nUse the admin",
            requirements="A computer with Python installed",
        )
        self.section = make_section(course=self.course)
        self.preview = make_lesson(
            self.section, title="A taste of the course", is_preview=True
        )
        make_lesson(self.section, title="The real work", order=2)

    def test_section_and_lesson_counts(self):
        self.assertEqual(self.course.section_count(), 1)
        self.assertEqual(self.course.lesson_count(), 2)

    def test_preview_lesson_returns_the_first_preview(self):
        self.assertEqual(self.course.preview_lesson(), self.preview)

    def test_no_preview_lesson_returns_none(self):
        other = make_course(title="No preview here")
        self.assertIsNone(other.preview_lesson())

    def test_detail_page_shows_counts_outcomes_and_preview(self):
        response = self.client.get(
            reverse("courses:detail", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1 section")
        self.assertContains(response, "2 lessons")
        self.assertContains(response, "&#10003; Build a Django app")
        self.assertContains(response, "Watch the free preview lesson")
        self.assertContains(response, "A taste of the course")

    def test_detail_page_without_preview_has_no_preview_callout(self):
        other = make_course(title="No preview here")
        response = self.client.get(reverse("courses:detail", args=[other.pk]))
        self.assertNotContains(response, "Watch the free preview lesson")
