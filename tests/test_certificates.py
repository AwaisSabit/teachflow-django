"""Tests for the certificate of completion."""
from django.test import TestCase
from django.urls import reverse

from apps.learning.models import (
    Certificate,
    Enrollment,
    LessonCompletion,
    QuizAttempt,
    is_eligible_for_certificate,
)
from tests.helpers import login_as, make_course, make_instructor, make_user
from tests.test_lessons import make_lesson, make_section
from tests.test_quiz_taking import make_question
from tests.test_quizzes import make_quiz


class CertificateTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.lesson = make_lesson(
            make_section(course=make_course(instructor=self.instructor))
        )
        self.course = self.lesson.section.course
        self.quiz = make_quiz(self.lesson, pass_mark=70)
        self.q1, self.q1_choices = make_question(self.quiz)
        self.student = make_user()
        self.enrollment = Enrollment.objects.create(
            student=self.student, course=self.course
        )
        login_as(self.client, self.student)

    def url(self):
        return reverse(
            "learning:certificate", kwargs={"course_pk": self.course.pk}
        )

    def finish_course(self):
        LessonCompletion.objects.create(
            enrollment=self.enrollment, lesson=self.lesson
        )
        QuizAttempt.objects.create(
            quiz=self.quiz, student=self.student, score=100, passed=True
        )

    def test_not_eligible_before_finishing(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not earned this certificate yet")
        self.assertContains(response, "0%")
        self.assertFalse(
            Certificate.objects.filter(enrollment=self.enrollment).exists()
        )

    def test_lessons_done_but_quiz_not_passed_is_not_eligible(self):
        LessonCompletion.objects.create(
            enrollment=self.enrollment, lesson=self.lesson
        )
        response = self.client.get(self.url())
        self.assertContains(response, "not earned this certificate yet")
        self.assertContains(response, "Quizzes passed: not yet")

    def test_full_completion_earns_the_certificate(self):
        self.finish_course()
        self.assertTrue(is_eligible_for_certificate(self.enrollment))
        response = self.client.get(self.url())
        self.assertContains(response, "Certificate of completion")
        self.assertContains(response, self.course.title)
        cert = Certificate.objects.get(enrollment=self.enrollment)
        self.assertEqual(cert.certificate_number, "TF-CERT-000001")
        self.assertContains(response, "TF-CERT-000001")

    def test_certificate_is_created_once(self):
        self.finish_course()
        self.client.get(self.url())
        self.client.get(self.url())
        self.assertEqual(
            Certificate.objects.filter(enrollment=self.enrollment).count(), 1
        )

    def test_certificate_numbers_are_sequential(self):
        self.finish_course()
        self.client.get(self.url())
        other_course = make_course(title="Second Course")
        other_enrollment = Enrollment.objects.create(
            student=self.student, course=other_course
        )
        Certificate.objects.create(enrollment=other_enrollment)
        second = Certificate.objects.get(enrollment=other_enrollment)
        self.assertEqual(second.certificate_number, "TF-CERT-000002")

    def test_non_enrolled_student_gets_a_403(self):
        login_as(self.client, make_user(username="outsider"))
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 403)

    def test_other_student_cannot_see_my_certificate(self):
        self.finish_course()
        self.client.get(self.url())
        login_as(self.client, make_user(username="other-student"))
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 403)

    def test_detail_page_links_to_the_certificate(self):
        response = self.client.get(
            reverse("courses:detail", args=[self.course.pk])
        )
        self.assertContains(response, "View my certificate")
