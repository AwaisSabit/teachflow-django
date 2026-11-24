"""End-to-end tests for TeachFlow.

One test walks the whole journey a real user takes: register as an
instructor, create and publish a course, add a quiz, register as a
student, enrol, finish the lessons, pass the quiz and earn the
certificate. A second test checks that a different user cannot see
or touch the first user's learning, orders or results.
"""
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.courses.models import Course
from apps.learning.models import (
    Certificate,
    Enrollment,
    LessonCompletion,
    Quiz,
    QuizAttempt,
)
from apps.payments.models import Order
from tests.helpers import TEST_PASSWORD

User = get_user_model()

PASSWORD = "LearnPass123!"


class FullJourneyTests(TestCase):
    def register(self, username, role):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": username,
                "email": f"{username}@example.com",
                "display_name": username.replace("-", " ").title(),
                "role": role,
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 302, response.context)
        return User.objects.get(username=username)

    def test_the_whole_journey(self):
        # 1. An instructor registers and logs in.
        teacher = self.register("journey-teacher", "instructor")
        self.assertTrue(teacher.is_instructor)

        # 2. The instructor creates a course — it starts as a draft.
        response = self.client.post(
            reverse("courses:create"),
            {
                "title": "Journey Course",
                "subtitle": "A course built end to end",
                "description": "Built by the test, taken by the test.",
                "price": "0",
                "level": "beginner",
                "language": "English",
                "category": self._category().pk,
                "what_you_will_learn": "Finish a course\nPass a quiz",
                "requirements": "Nothing",
            },
        )
        course = Course.objects.get(title="Journey Course")
        self.assertRedirects(response, reverse("courses:my_courses"))
        self.assertEqual(course.status, Course.Status.DRAFT)

        # 3. A section and two lessons, the first one a free preview.
        response = self.client.post(
            reverse("courses:section_create", args=[course.pk]),
            {"title": "Getting started", "order": 1},
        )
        section = course.sections.get(title="Getting started")
        lesson1 = self._make_lesson(section, "Lesson One", preview=True)
        lesson2 = self._make_lesson(section, "Lesson Two")

        # 4. The instructor adds a quiz to the first lesson.
        response = self.client.post(
            reverse("learning:quiz_create", args=[lesson1.pk]),
            {"title": "Check what you learned", "pass_mark": 70},
        )
        quiz = Quiz.objects.get(lesson=lesson1)
        self.assertRedirects(
            response,
            reverse("learning:quiz_manage", kwargs={"quiz_pk": quiz.pk}),
        )
        self.client.post(
            reverse("learning:quiz_manage", kwargs={"quiz_pk": quiz.pk}),
            {
                "text": "What is 2 + 2?",
                "choice_a": "4",
                "choice_b": "3",
                "choice_c": "5",
                "choice_d": "6",
                "correct": "a",
            },
        )
        self.assertEqual(quiz.questions.count(), 1)

        # 5. The instructor submits and publishes the course.
        self.client.post(reverse("courses:submit", args=[course.pk]))
        self.client.post(reverse("courses:publish", args=[course.pk]))
        course.refresh_from_db()
        self.assertEqual(course.status, Course.Status.PUBLISHED)

        # 6. A student registers, finds the course and enrols for free.
        self.client.logout()
        student = self.register("journey-student", "student")
        response = self.client.get(reverse("courses:browse"))
        self.assertContains(response, "Journey Course")
        response = self.client.post(reverse("learning:enrol", args=[course.pk]))
        self.assertRedirects(
            response, reverse("courses:detail", args=[course.pk])
        )
        enrollment = Enrollment.objects.get(student=student, course=course)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Journey Course", mail.outbox[0].subject)

        # 7. The student reads both lessons and marks them complete.
        for lesson in (lesson1, lesson2):
            response = self.client.get(
                reverse("courses:lesson_detail", args=[lesson.pk])
            )
            self.assertEqual(response.status_code, 200)
            self.client.post(
                reverse("learning:toggle_complete", args=[lesson.pk])
            )
        self.assertEqual(
            LessonCompletion.objects.filter(enrollment=enrollment).count(), 2
        )

        # 8. The student takes the quiz and passes it.
        question = quiz.questions.get()
        choice = question.choices.get(is_correct=True)
        response = self.client.post(
            reverse("learning:quiz_take", kwargs={"quiz_pk": quiz.pk}),
            {f"question_{question.pk}": str(choice.pk)},
        )
        attempt = QuizAttempt.objects.get(quiz=quiz, student=student)
        self.assertRedirects(
            response,
            reverse("learning:quiz_result", args=[attempt.pk]),
        )
        self.assertEqual(attempt.score, 100)
        self.assertTrue(attempt.passed)

        # 9. The certificate is waiting.
        response = self.client.get(
            reverse("learning:certificate", kwargs={"course_pk": course.pk})
        )
        self.assertContains(response, "Certificate of completion")
        self.assertContains(response, "Journey Course")
        cert = Certificate.objects.get(enrollment=enrollment)
        self.assertEqual(cert.certificate_number, "TF-CERT-000001")
        self.assertEqual(len(mail.outbox), 2)

        # 10. The student's dashboard shows the finished course.
        response = self.client.get(reverse("learning:student_dashboard"))
        self.assertContains(response, "Journey Course")
        self.assertContains(response, "100%")
        self.assertContains(response, "Course complete")

    def test_second_user_cannot_see_or_touch_the_first_users_learning(self):
        teacher = self.register("leak-teacher", "instructor")
        course = self._published_course(teacher)
        section = course.sections.get(title="Getting started")
        lesson = section.lessons.get(title="Lesson One")

        # The first student enrols, finishes the lesson and buys nothing.
        self.client.logout()
        first = self.register("first-student", "student")
        self.client.post(reverse("learning:enrol", args=[course.pk]))
        self.client.post(reverse("learning:toggle_complete", args=[lesson.pk]))

        # A second student cannot see the first student's progress,
        # certificate, quiz results or purchase history.
        self.client.logout()
        self.register("second-student", "student")
        response = self.client.get(
            reverse("learning:certificate", kwargs={"course_pk": course.pk})
        )
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse("learning:student_dashboard"))
        self.assertNotContains(response, "Journey Course")
        response = self.client.get(reverse("payments:history"))
        self.assertContains(response, "not bought any courses yet")

        # The second student cannot complete lessons for the first
        # student's enrolment, and cannot see a draft course at all.
        response = self.client.post(
            reverse("learning:toggle_complete", args=[lesson.pk])
        )
        self.assertEqual(response.status_code, 403)
        draft = self._draft_course(teacher)
        response = self.client.get(
            reverse("courses:detail", args=[draft.pk])
        )
        self.assertEqual(response.status_code, 404)

        # The first student's data is untouched by the second user.
        enrollment = Enrollment.objects.get(student=first, course=course)
        self.assertEqual(enrollment.completions.count(), 1)
        self.assertEqual(Order.objects.filter(student=first).count(), 0)

    def _category(self):
        from tests.helpers import make_category

        return make_category(name="Journey")

    def _make_lesson(self, section, title, preview=False):
        from tests.test_lessons import make_lesson

        return make_lesson(section, title=title, is_preview=preview)

    def _published_course(self, teacher):
        from tests.helpers import make_course
        from tests.test_lessons import make_lesson, make_section

        course = make_course(instructor=teacher, title="Journey Course")
        section = make_section(course=course, title="Getting started")
        make_lesson(section, title="Lesson One", is_preview=True)
        return course

    def _draft_course(self, teacher):
        from tests.helpers import make_course

        return make_course(
            instructor=teacher,
            title="Hidden Draft",
            status=Course.Status.DRAFT,
        )
