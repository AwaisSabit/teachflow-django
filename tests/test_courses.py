"""Tests for the Course model and instructor course management."""
from django.test import TestCase
from django.urls import reverse

from apps.courses.models import Course
from tests.helpers import (
    TEST_PASSWORD,
    login_as,
    make_category,
    make_course,
    make_instructor,
    make_user,
)

CREATE_URL = reverse("courses:create")
MY_COURSES_URL = reverse("courses:my_courses")


def course_data(**overrides):
    data = {
        "title": "Django for Beginners",
        "subtitle": "Build your first web app.",
        "description": "A friendly first course in Django.",
        "price": "49.99",
        "level": "beginner",
        "language": "English",
        "thumbnail_url": "",
        "what_you_will_learn": "Build a Django app\nUse the admin",
        "requirements": "A computer with Python installed",
    }
    data.update(overrides)
    return data


class CourseModelTests(TestCase):
    def test_new_course_is_a_draft(self):
        course = make_course(status=Course.Status.DRAFT)
        self.assertEqual(course.status, Course.Status.DRAFT)
        self.assertFalse(course.is_published)

    def test_free_course_when_price_is_zero(self):
        free = make_course(price=0)
        paid = make_course(price=49.99, title="Paid Course")
        self.assertTrue(free.is_free)
        self.assertFalse(paid.is_free)

    def test_learning_outcomes_split_lines(self):
        course = make_course(
            what_you_will_learn="Build an app\n\nUse the admin\n  "
        )
        self.assertEqual(
            course.learning_outcomes(), ["Build an app", "Use the admin"]
        )

    def test_str_is_the_title(self):
        course = make_course(title="Django for Beginners")
        self.assertEqual(str(course), "Django for Beginners")


class CourseCreateTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.category = make_category()
        login_as(self.client, self.instructor)

    def test_create_page_loads_for_instructors(self):
        response = self.client.get(CREATE_URL)
        self.assertEqual(response.status_code, 200)

    def test_create_saves_a_draft_owned_by_the_instructor(self):
        response = self.client.post(
            CREATE_URL, course_data(category=self.category.pk)
        )
        self.assertRedirects(response, MY_COURSES_URL)
        course = Course.objects.get(title="Django for Beginners")
        self.assertEqual(course.instructor, self.instructor)
        self.assertEqual(course.status, Course.Status.DRAFT)
        from decimal import Decimal
        self.assertEqual(course.price, Decimal("49.99"))

    def test_create_rejects_a_negative_price(self):
        response = self.client.post(
            CREATE_URL,
            course_data(category=self.category.pk, price="-5"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Course.objects.filter(title="Django for Beginners").exists())

    def test_student_cannot_open_the_create_page(self):
        student = make_user(username="student1")
        login_as(self.client, student)
        response = self.client.get(CREATE_URL)
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(CREATE_URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])


class CourseEditDeleteTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.other = make_instructor(username="other")
        self.course = make_course(instructor=self.instructor)
        login_as(self.client, self.instructor)

    def test_edit_updates_the_course(self):
        response = self.client.post(
            reverse("courses:edit", args=[self.course.pk]),
            course_data(category=self.course.category.pk, title="Django Pro"),
        )
        self.assertRedirects(response, MY_COURSES_URL)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Django Pro")

    def test_edit_is_404_for_another_instructors_course(self):
        login_as(self.client, self.other)
        response = self.client.get(
            reverse("courses:edit", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_removes_the_course_after_confirm(self):
        response = self.client.post(
            reverse("courses:delete", args=[self.course.pk])
        )
        self.assertRedirects(response, MY_COURSES_URL)
        self.assertFalse(Course.objects.filter(pk=self.course.pk).exists())

    def test_delete_is_404_for_another_instructors_course(self):
        login_as(self.client, self.other)
        response = self.client.post(
            reverse("courses:delete", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Course.objects.filter(pk=self.course.pk).exists())

    def test_my_courses_lists_only_my_own(self):
        make_course(instructor=self.other, title="Someone Else's Course")
        response = self.client.get(MY_COURSES_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python for Beginners")
        self.assertNotContains(response, "Someone Else's Course")
