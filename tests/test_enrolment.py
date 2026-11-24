"""Tests for free enrolment and the lesson gate."""
from django.test import TestCase
from django.urls import reverse

from apps.courses.models import Course
from apps.learning.models import Enrollment, is_enrolled
from tests.helpers import login_as, make_course, make_instructor, make_user
from tests.test_lessons import make_lesson, make_section


class FreeEnrolmentTests(TestCase):
    def setUp(self):
        self.student = make_user()
        self.course = make_course(price=0)
        login_as(self.client, self.student)

    def test_free_enrolment_creates_an_enrolment(self):
        response = self.client.post(
            reverse("learning:enrol", args=[self.course.pk])
        )
        self.assertRedirects(
            response, reverse("courses:detail", args=[self.course.pk])
        )
        self.assertTrue(
            Enrollment.objects.filter(
                student=self.student, course=self.course
            ).exists()
        )

    def test_enrolling_twice_creates_only_one_enrolment(self):
        url = reverse("learning:enrol", args=[self.course.pk])
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(
            Enrollment.objects.filter(
                student=self.student, course=self.course
            ).count(),
            1,
        )

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.post(
            reverse("learning:enrol", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_paid_course_cannot_be_enrolled_on_directly(self):
        paid = make_course(price=49.99, title="Paid Course")
        response = self.client.post(reverse("learning:enrol", args=[paid.pk]))
        self.assertRedirects(
            response, reverse("courses:detail", args=[paid.pk])
        )
        self.assertFalse(
            Enrollment.objects.filter(student=self.student, course=paid).exists()
        )

    def test_draft_course_cannot_be_enrolled_on(self):
        draft = make_course(status=Course.Status.DRAFT, title="Drafty")
        response = self.client.post(reverse("learning:enrol", args=[draft.pk]))
        self.assertEqual(response.status_code, 404)

    def test_get_does_not_enrol(self):
        response = self.client.get(
            reverse("learning:enrol", args=[self.course.pk])
        )
        self.assertRedirects(
            response, reverse("courses:detail", args=[self.course.pk])
        )
        self.assertFalse(
            Enrollment.objects.filter(
                student=self.student, course=self.course
            ).exists()
        )

    def test_is_enrolled_helper(self):
        self.assertFalse(is_enrolled(self.student, self.course))
        Enrollment.objects.create(student=self.student, course=self.course)
        self.assertTrue(is_enrolled(self.student, self.course))

    def test_detail_page_shows_enrolled_state(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        response = self.client.get(
            reverse("courses:detail", args=[self.course.pk])
        )
        self.assertContains(response, "You are enrolled on this course.")


class LessonGateTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.course = make_course(instructor=self.instructor, price=0)
        self.section = make_section(course=self.course)
        self.preview = make_lesson(
            self.section, title="Preview", is_preview=True
        )
        self.lesson = make_lesson(self.section, title="Real lesson", order=2)
        self.student = make_user()

    def test_preview_lesson_is_open_to_everyone(self):
        response = self.client.get(
            reverse("courses:lesson_detail", args=[self.preview.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_non_preview_lesson_is_403_without_enrolment(self):
        login_as(self.client, self.student)
        response = self.client.get(
            reverse("courses:lesson_detail", args=[self.lesson.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_enrolled_student_can_watch_the_lesson(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        login_as(self.client, self.student)
        response = self.client.get(
            reverse("courses:lesson_detail", args=[self.lesson.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_instructor_can_watch_their_own_lessons(self):
        login_as(self.client, self.instructor)
        response = self.client.get(
            reverse("courses:lesson_detail", args=[self.lesson.pk])
        )
        self.assertEqual(response.status_code, 200)
