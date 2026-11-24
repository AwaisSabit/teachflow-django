"""Tests for the demo seed command."""
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.courses.models import Category, Course, Lesson, Review
from apps.learning.models import Enrollment, Quiz
from apps.payments.models import Coupon
from tests.helpers import TEST_PASSWORD

User = get_user_model()


@override_settings(DEBUG=True)
class SeedDemoTests(TestCase):
    def test_seed_creates_the_demo_accounts(self):
        call_command("seed_demo")
        teacher = User.objects.get(username="demo-teacher")
        self.assertTrue(teacher.is_instructor)
        student = User.objects.get(username="demo-student")
        self.assertTrue(student.is_student)
        self.assertTrue(
            self.client.login(username="demo-teacher", password="DemoPass123!")
        )
        self.assertTrue(
            self.client.login(username="demo-student", password="DemoPass123!")
        )

    def test_seed_creates_categories_courses_and_curriculum(self):
        call_command("seed_demo")
        self.assertEqual(Category.objects.count(), 3)
        self.assertEqual(Course.objects.count(), 4)
        self.assertEqual(Lesson.objects.count(), 14)
        python = Course.objects.get(title="Python for Beginners")
        self.assertEqual(python.status, Course.Status.PUBLISHED)
        self.assertEqual(python.sections.count(), 2)
        self.assertEqual(python.lesson_count(), 4)
        draft = Course.objects.get(title="Freelancing 101")
        self.assertEqual(draft.status, Course.Status.DRAFT)

    def test_seed_creates_quizzes_enrolments_and_reviews(self):
        call_command("seed_demo")
        self.assertEqual(Quiz.objects.count(), 3)
        student = User.objects.get(username="demo-student")
        self.assertEqual(
            Enrollment.objects.filter(student=student).count(), 3
        )
        self.assertEqual(Review.objects.count(), 2)
        self.assertEqual(Coupon.objects.filter(code="LEARN20").count(), 1)

    def test_seed_is_idempotent(self):
        call_command("seed_demo")
        call_command("seed_demo")
        self.assertEqual(Category.objects.count(), 3)
        self.assertEqual(Course.objects.count(), 4)
        self.assertEqual(Lesson.objects.count(), 14)
        self.assertEqual(Quiz.objects.count(), 3)
        self.assertEqual(Review.objects.count(), 2)
        self.assertEqual(
            User.objects.filter(username__startswith="demo-").count(), 2
        )

    def test_seeded_courses_show_on_the_browse_page(self):
        call_command("seed_demo")
        response = self.client.get(reverse("courses:browse"))
        self.assertContains(response, "Python for Beginners")
        self.assertContains(response, "Django in Practice")
        self.assertContains(response, "UI Design Basics")
        self.assertNotContains(response, "Freelancing 101")

    def test_clear_wipes_and_reseeds(self):
        call_command("seed_demo")
        call_command("seed_demo", "--clear")
        self.assertEqual(Category.objects.count(), 3)
        self.assertEqual(Course.objects.count(), 4)
        self.assertEqual(
            User.objects.filter(username__startswith="demo-").count(), 2
        )
