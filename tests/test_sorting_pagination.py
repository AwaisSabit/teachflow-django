"""Tests for sorting and pagination on the course lists."""
from django.test import TestCase
from django.urls import reverse

from tests.helpers import make_category, make_course

BROWSE_URL = reverse("courses:browse")


class SortingTests(TestCase):
    def setUp(self):
        self.category = make_category()
        self.cheap = make_course(
            category=self.category, title="Cheap Course", price=9.99
        )
        self.expensive = make_course(
            category=self.category, title="Expensive Course", price=99.99
        )
        self.free = make_course(
            category=self.category, title="Free Course", price=0
        )

    def _titles_in_order(self, response):
        body = response.content.decode()
        return [t for t in ("Free Course", "Cheap Course", "Expensive Course") if t in body]

    def test_default_sort_is_newest_first(self):
        response = self.client.get(BROWSE_URL)
        body = response.content.decode()
        # Created last first: free, then expensive, then cheap.
        self.assertLess(body.index("Free Course"), body.index("Expensive Course"))
        self.assertLess(body.index("Expensive Course"), body.index("Cheap Course"))

    def test_sort_by_price_low_to_high(self):
        response = self.client.get(BROWSE_URL, {"sort": "price_low"})
        body = response.content.decode()
        self.assertLess(body.index("Free Course"), body.index("Cheap Course"))
        self.assertLess(body.index("Cheap Course"), body.index("Expensive Course"))

    def test_sort_by_price_high_to_low(self):
        response = self.client.get(BROWSE_URL, {"sort": "price_high"})
        body = response.content.decode()
        self.assertLess(body.index("Expensive Course"), body.index("Cheap Course"))
        self.assertLess(body.index("Cheap Course"), body.index("Free Course"))

    def test_sort_by_title(self):
        response = self.client.get(BROWSE_URL, {"sort": "title"})
        body = response.content.decode()
        self.assertLess(body.index("Cheap Course"), body.index("Expensive Course"))
        self.assertLess(body.index("Expensive Course"), body.index("Free Course"))

    def test_unknown_sort_falls_back_to_newest(self):
        response = self.client.get(BROWSE_URL, {"sort": "random"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Free Course")


class PaginationTests(TestCase):
    def test_browse_paginates_ten_per_page(self):
        category = make_category()
        for i in range(12):
            make_course(category=category, title=f"Course {i:02d}")
        response = self.client.get(BROWSE_URL)
        self.assertEqual(len(response.context["page_obj"]), 10)
        self.assertTrue(response.context["page_obj"].has_next())
        response = self.client.get(BROWSE_URL, {"page": 2})
        self.assertEqual(len(response.context["page_obj"]), 2)
        self.assertFalse(response.context["page_obj"].has_next())

    def test_page_links_keep_the_filters(self):
        category = make_category()
        for i in range(11):
            make_course(category=category, title=f"Free {i:02d}", price=0)
        make_course(category=category, title="Paid One", price=10)
        response = self.client.get(BROWSE_URL, {"price": "free", "page": 2})
        self.assertEqual(response.status_code, 200)
        self.assertIn("price=free", response.content.decode())

    def test_out_of_range_page_shows_the_last_page(self):
        make_course()
        response = self.client.get(BROWSE_URL, {"page": 99})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python for Beginners")

    def test_category_page_paginates(self):
        category = make_category()
        for i in range(11):
            make_course(category=category, title=f"Cat Course {i:02d}")
        response = self.client.get(
            reverse("courses:category", args=[category.slug])
        )
        self.assertEqual(len(response.context["page_obj"]), 10)
        response = self.client.get(
            reverse("courses:category", args=[category.slug]), {"page": 2}
        )
        self.assertEqual(len(response.context["page_obj"]), 1)
