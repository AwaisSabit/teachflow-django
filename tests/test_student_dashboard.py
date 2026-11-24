"""Tests for the student dashboard."""
from django.test import TestCase
from django.urls import reverse

from apps.learning.models import (
    Enrollment,
    LessonCompletion,
    QuizAttempt,
)
from tests.helpers import login_as, make_course, make_instructor, make_user
from tests.test_lessons import make_lesson, make_section
from tests.test_quiz_taking import make_question
from tests.test_quizzes import make_quiz


class StudentDashboardTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.course = make_course(instructor=self.instructor)
        self.section = make_section(course=self.course)
        self.lesson1 = make_lesson(self.section, title="Lesson One")
        self.lesson2 = make_lesson(self.section, title="Lesson Two", order=2)
        self.student = make_user()
        self.enrollment = Enrollment.objects.create(
            student=self.student, course=self.course
        )
        login_as(self.client, self.student)

    def url(self):
        return reverse("learning:student_dashboard")

    def test_dashboard_lists_my_courses_with_progress(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python for Beginners")
        self.assertContains(response, "0%")

    def test_continue_points_to_the_first_lesson(self):
        response = self.client.get(self.url())
        self.assertContains(response, "Continue: Lesson One")
        self.assertContains(
            response,
            reverse("courses:lesson_detail", args=[self.lesson1.pk]),
        )

    def test_continue_moves_on_after_finishing_a_lesson(self):
        LessonCompletion.objects.create(
            enrollment=self.enrollment, lesson=self.lesson1
        )
        response = self.client.get(self.url())
        self.assertContains(response, "Continue: Lesson Two")
        self.assertContains(response, "50%")

    def test_finished_course_shows_the_certificate_link(self):
        quiz = make_quiz(self.lesson1)
        make_question(quiz)
        LessonCompletion.objects.create(
            enrollment=self.enrollment, lesson=self.lesson1
        )
        LessonCompletion.objects.create(
            enrollment=self.enrollment, lesson=self.lesson2
        )
        QuizAttempt.objects.create(
            quiz=quiz, student=self.student, score=100, passed=True
        )
        response = self.client.get(self.url())
        self.assertContains(response, "Course complete")
        self.assertContains(response, "View my certificate")

    def test_courses_i_am_not_enrolled_on_do_not_show(self):
        make_course(title="Another Course")
        response = self.client.get(self.url())
        self.assertNotContains(response, "Another Course")

    def test_empty_state(self):
        login_as(self.client, make_user(username="new-student"))
        response = self.client.get(self.url())
        self.assertContains(response, "not enrolled on any courses yet")

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
