"""Tests for email notifications (console backend in dev, locmem
in tests)."""
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.courses.models import Announcement
from apps.learning.models import (
    Enrollment,
    LessonCompletion,
    QuizAttempt,
)
from tests.helpers import login_as, make_course, make_instructor, make_user
from tests.test_lessons import make_lesson, make_section
from tests.test_quiz_taking import make_question
from tests.test_quizzes import make_quiz


def make_student_with_email(username="layla-student"):
    user = make_user(username=username)
    user.email = f"{username}@example.com"
    user.save()
    return user


class NotificationTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.course = make_course(instructor=self.instructor)
        self.student = make_student_with_email()
        login_as(self.client, self.student)

    def test_free_enrolment_sends_an_email(self):
        free = make_course(price=0, title="Free Course")
        self.client.post(reverse("learning:enrol", args=[free.pk]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Free Course", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ["layla-student@example.com"])

    def test_enrolling_twice_sends_one_email(self):
        free = make_course(price=0, title="Free Course")
        self.client.post(reverse("learning:enrol", args=[free.pk]))
        self.client.post(reverse("learning:enrol", args=[free.pk]))
        self.assertEqual(len(mail.outbox), 1)

    def test_certificate_email_is_sent_once(self):
        lesson = make_lesson(make_section(course=self.course))
        quiz = make_quiz(lesson)
        make_question(quiz)
        Enrollment.objects.create(student=self.student, course=self.course)
        LessonCompletion.objects.create(
            enrollment=Enrollment.objects.get(
                student=self.student, course=self.course
            ),
            lesson=lesson,
        )
        QuizAttempt.objects.create(
            quiz=quiz, student=self.student, score=100, passed=True
        )
        url = reverse(
            "learning:certificate", kwargs={"course_pk": self.course.pk}
        )
        self.client.get(url)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("certificate", mail.outbox[0].subject.lower())
        self.assertIn("TF-CERT-000001", mail.outbox[0].body)
        self.client.get(url)
        self.assertEqual(len(mail.outbox), 1)

    def test_announcement_email_goes_to_enrolled_students_only(self):
        other = make_student_with_email("other-student")
        Enrollment.objects.create(student=self.student, course=self.course)
        login_as(self.client, self.instructor)
        self.client.post(
            reverse("courses:announcement_create", args=[self.course.pk]),
            {"title": "New lesson", "body": "Lesson 5 is live."},
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["layla-student@example.com"])
        self.assertIn("New lesson", mail.outbox[0].subject)
        self.assertNotIn(other.email, str(mail.outbox[0].to))

    def test_no_email_when_the_student_has_no_address(self):
        student = make_user(username="no-email")
        student.email = ""
        student.save()
        login_as(self.client, student)
        free = make_course(price=0, title="Free Course")
        response = self.client.post(reverse("learning:enrol", args=[free.pk]))
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(response.status_code, 302)
