"""Tests for course ratings and reviews."""
from django.test import TestCase
from django.urls import reverse

from apps.courses.models import Review
from apps.learning.models import Enrollment
from tests.helpers import login_as, make_course, make_user


class ReviewTests(TestCase):
    def setUp(self):
        self.student = make_user()
        self.other = make_user(username="other-student")
        self.course = make_course()
        Enrollment.objects.create(student=self.student, course=self.course)
        login_as(self.client, self.student)

    def review_url(self, course=None):
        return reverse("courses:review", args=[(course or self.course).pk])

    def test_enrolled_student_can_review(self):
        response = self.client.post(
            self.review_url(), {"rating": 5, "comment": "Excellent course!"}
        )
        self.assertRedirects(
            response, reverse("courses:detail", args=[self.course.pk])
        )
        review = Review.objects.get(course=self.course, student=self.student)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, "Excellent course!")

    def test_reviewing_again_updates_instead_of_duplicating(self):
        self.client.post(self.review_url(), {"rating": 5, "comment": "Great"})
        self.client.post(self.review_url(), {"rating": 3, "comment": "Changed my mind"})
        self.assertEqual(
            Review.objects.filter(course=self.course, student=self.student).count(),
            1,
        )
        review = Review.objects.get(course=self.course, student=self.student)
        self.assertEqual(review.rating, 3)
        self.assertEqual(review.comment, "Changed my mind")

    def test_non_enrolled_student_cannot_review(self):
        login_as(self.client, self.other)
        response = self.client.post(
            self.review_url(), {"rating": 5, "comment": "Never took it"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Review.objects.filter(course=self.course, student=self.other).exists()
        )

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(self.review_url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_rating_below_one_is_rejected(self):
        response = self.client.post(
            self.review_url(), {"rating": 0, "comment": "Too low"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Review.objects.filter(course=self.course, student=self.student).exists()
        )

    def test_rating_above_five_is_rejected(self):
        response = self.client.post(
            self.review_url(), {"rating": 6, "comment": "Too high"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Review.objects.filter(course=self.course, student=self.student).exists()
        )

    def test_average_rating_shows_on_the_detail_page(self):
        Review.objects.create(
            course=self.course, student=self.student, rating=5, comment="Great"
        )
        Enrollment.objects.create(student=self.other, course=self.course)
        Review.objects.create(
            course=self.course, student=self.other, rating=3, comment="Okay"
        )
        response = self.client.get(
            reverse("courses:detail", args=[self.course.pk])
        )
        self.assertContains(response, "4.0 out of 5")
        self.assertContains(response, "2 reviews")
        self.assertContains(response, "Great")

    def test_detail_page_without_reviews_says_so(self):
        response = self.client.get(
            reverse("courses:detail", args=[self.course.pk])
        )
        self.assertContains(response, "No reviews yet.")
