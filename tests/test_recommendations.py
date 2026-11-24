"""Tests for course recommendations ("students also bought")."""
from django.test import TestCase
from django.urls import reverse

from apps.learning.models import Enrollment
from tests.helpers import login_as, make_category, make_course, make_user


class RecommendationTests(TestCase):
    def setUp(self):
        self.category = make_category(name="Programming")
        self.course = make_course(category=self.category)
        self.student = make_user()
        login_as(self.client, self.student)

    def detail_url(self, course=None):
        return reverse("courses:detail", args=[(course or self.course).pk])

    def test_same_category_courses_are_recommended(self):
        other = make_course(category=self.category, title="Django Deep Dive")
        response = self.client.get(self.detail_url())
        self.assertContains(response, "Students also bought")
        self.assertContains(response, "Django Deep Dive")

    def test_other_categories_are_not_recommended(self):
        make_course(
            category=make_category(name="Design"), title="Design Basics"
        )
        response = self.client.get(self.detail_url())
        self.assertNotContains(response, "Design Basics")

    def test_the_course_itself_is_not_recommended(self):
        response = self.client.get(self.detail_url())
        self.assertNotContains(response, "Students also bought")

    def test_draft_courses_are_not_recommended(self):
        from apps.courses.models import Course

        make_course(
            category=self.category,
            title="Unpublished Course",
            status=Course.Status.DRAFT,
        )
        response = self.client.get(self.detail_url())
        self.assertNotContains(response, "Unpublished Course")

    def test_most_enrolled_courses_come_first(self):
        popular = make_course(category=self.category, title="Popular Course")
        quiet = make_course(category=self.category, title="Quiet Course")
        for i in range(3):
            Enrollment.objects.create(
                student=make_user(username=f"buyer-{i}"), course=popular
            )
        Enrollment.objects.create(student=self.student, course=quiet)
        response = self.client.get(self.detail_url())
        content = response.content.decode()
        self.assertLess(
            content.index("Popular Course"), content.index("Quiet Course")
        )

    def test_at_most_four_recommendations(self):
        for i in range(5):
            make_course(
                category=self.category, title=f"Extra Course {i}"
            )
        response = self.client.get(self.detail_url())
        self.assertEqual(
            len(response.context["recommendations"]), 4
        )
