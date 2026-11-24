"""Tests for the wishlist."""
from django.test import TestCase
from django.urls import reverse

from apps.payments.models import WishlistItem
from tests.helpers import login_as, make_course, make_user


class WishlistTests(TestCase):
    def setUp(self):
        self.student = make_user()
        self.course = make_course()
        login_as(self.client, self.student)

    def test_add_saves_the_course(self):
        response = self.client.post(
            reverse("payments:wishlist_add", args=[self.course.pk])
        )
        self.assertRedirects(
            response, reverse("courses:detail", args=[self.course.pk])
        )
        self.assertTrue(
            WishlistItem.objects.filter(
                student=self.student, course=self.course
            ).exists()
        )

    def test_adding_twice_keeps_one_item(self):
        url = reverse("payments:wishlist_add", args=[self.course.pk])
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(
            WishlistItem.objects.filter(
                student=self.student, course=self.course
            ).count(),
            1,
        )

    def test_wishlist_page_lists_saved_courses(self):
        WishlistItem.objects.create(student=self.student, course=self.course)
        other = make_course(title="Another Course")
        response = self.client.get(reverse("payments:wishlist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python for Beginners")
        self.assertNotContains(response, "Another Course")

    def test_wishlist_page_empty_state(self):
        response = self.client.get(reverse("payments:wishlist"))
        self.assertContains(response, "Your wishlist is empty.")

    def test_remove_takes_the_course_off(self):
        WishlistItem.objects.create(student=self.student, course=self.course)
        response = self.client.post(
            reverse("payments:wishlist_remove", args=[self.course.pk])
        )
        self.assertRedirects(response, reverse("payments:wishlist"))
        self.assertFalse(
            WishlistItem.objects.filter(
                student=self.student, course=self.course
            ).exists()
        )

    def test_wishlist_is_per_user(self):
        WishlistItem.objects.create(student=self.student, course=self.course)
        other_user = make_user(username="someone-else")
        login_as(self.client, other_user)
        response = self.client.get(reverse("payments:wishlist"))
        self.assertNotContains(response, "Python for Beginners")

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.post(
            reverse("payments:wishlist_add", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_get_does_not_add_to_wishlist(self):
        self.client.get(reverse("payments:wishlist_add", args=[self.course.pk]))
        self.assertFalse(
            WishlistItem.objects.filter(
                student=self.student, course=self.course
            ).exists()
        )
