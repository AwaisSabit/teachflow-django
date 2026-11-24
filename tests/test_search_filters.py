"""Tests for course search and filters on the browse page."""
from django.test import TestCase
from django.urls import reverse

from apps.courses.models import Course
from tests.helpers import make_category, make_course

BROWSE_URL = reverse("courses:browse")


class SearchFilterTests(TestCase):
    def setUp(self):
        self.python = make_category(name="Python")
        self.design = make_category(name="Design")
        self.django_course = make_course(
            category=self.python,
            title="Django for Beginners",
            subtitle="Build your first web app.",
            description="A friendly first course in Django.",
            level=Course.Level.BEGINNER,
            price=0,
        )
        self.flask_course = make_course(
            category=self.python,
            title="Flask in a Weekend",
            subtitle="Small apps, fast.",
            description="Microframeworks and APIs.",
            level=Course.Level.INTERMEDIATE,
            price=29.99,
        )
        self.design_course = make_course(
            category=self.design,
            title="Figma for Beginners",
            subtitle="Design interfaces that look good.",
            description="Learn Figma from scratch.",
            level=Course.Level.BEGINNER,
            price=0,
        )
        self.draft = make_course(
            category=self.python,
            title="Unpublished Django Secrets",
            status=Course.Status.DRAFT,
        )

    def test_browse_lists_only_published_courses(self):
        response = self.client.get(BROWSE_URL)
        self.assertContains(response, "Django for Beginners")
        self.assertContains(response, "Flask in a Weekend")
        self.assertContains(response, "Figma for Beginners")
        self.assertNotContains(response, "Unpublished Django Secrets")

    def test_search_finds_by_title(self):
        response = self.client.get(BROWSE_URL, {"q": "Flask"})
        self.assertContains(response, "Flask in a Weekend")
        self.assertNotContains(response, "Django for Beginners")
        self.assertNotContains(response, "Figma for Beginners")

    def test_search_finds_by_subtitle_and_description(self):
        response = self.client.get(BROWSE_URL, {"q": "Microframeworks"})
        self.assertContains(response, "Flask in a Weekend")
        response = self.client.get(BROWSE_URL, {"q": "interfaces"})
        self.assertContains(response, "Figma for Beginners")

    def test_search_is_case_insensitive(self):
        response = self.client.get(BROWSE_URL, {"q": "django"})
        self.assertContains(response, "Django for Beginners")

    def test_search_with_no_match_shows_empty_state(self):
        response = self.client.get(BROWSE_URL, {"q": "quantum"})
        self.assertContains(response, "No courses match those filters.")

    def test_category_filter(self):
        response = self.client.get(BROWSE_URL, {"category": "design"})
        self.assertContains(response, "Figma for Beginners")
        self.assertNotContains(response, "Django for Beginners")
        self.assertNotContains(response, "Flask in a Weekend")

    def test_level_filter(self):
        response = self.client.get(BROWSE_URL, {"level": "intermediate"})
        self.assertContains(response, "Flask in a Weekend")
        self.assertNotContains(response, "Django for Beginners")

    def test_free_filter(self):
        response = self.client.get(BROWSE_URL, {"price": "free"})
        self.assertContains(response, "Django for Beginners")
        self.assertContains(response, "Figma for Beginners")
        self.assertNotContains(response, "Flask in a Weekend")

    def test_paid_filter(self):
        response = self.client.get(BROWSE_URL, {"price": "paid"})
        self.assertContains(response, "Flask in a Weekend")
        self.assertNotContains(response, "Django for Beginners")

    def test_filters_combine(self):
        response = self.client.get(
            BROWSE_URL, {"category": "python", "price": "free"}
        )
        self.assertContains(response, "Django for Beginners")
        self.assertNotContains(response, "Flask in a Weekend")
        self.assertNotContains(response, "Figma for Beginners")

    def test_unknown_level_value_is_ignored(self):
        response = self.client.get(BROWSE_URL, {"level": "expert"})
        self.assertContains(response, "Django for Beginners")
        self.assertContains(response, "Flask in a Weekend")
