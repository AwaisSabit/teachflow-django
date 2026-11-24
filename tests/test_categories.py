"""Tests for course categories and browsing."""
from django.test import TestCase
from django.urls import reverse

from apps.courses.models import Category
from tests.helpers import make_category


class CategoryModelTests(TestCase):
    def test_slug_is_made_from_the_name(self):
        category = make_category(name="Web Development")
        self.assertEqual(category.slug, "web-development")

    def test_explicit_slug_is_kept(self):
        category = Category.objects.create(
            name="Data Science", slug="data", description=""
        )
        self.assertEqual(category.slug, "data")

    def test_names_are_unique(self):
        make_category(name="Python")
        with self.assertRaises(Exception):
            make_category(name="Python")

    def test_categories_order_by_name(self):
        make_category(name="Python")
        make_category(name="Design")
        make_category(name="Business")
        names = list(Category.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Business", "Design", "Python"])


class BrowseTests(TestCase):
    def test_browse_lists_categories_for_everyone(self):
        make_category(name="Python")
        make_category(name="Design")
        response = self.client.get(reverse("courses:browse"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python")
        self.assertContains(response, "Design")

    def test_browse_empty_state(self):
        response = self.client.get(reverse("courses:browse"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No courses match those filters.")

    def test_category_page_shows_description_and_empty_state(self):
        category = make_category(
            name="Python", description="Learn Python from scratch."
        )
        response = self.client.get(
            reverse("courses:category", args=[category.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Learn Python from scratch.")
        self.assertContains(response, "No courses in this category yet.")

    def test_unknown_category_is_404(self):
        response = self.client.get(reverse("courses:category", args=["nope"]))
        self.assertEqual(response.status_code, 404)
