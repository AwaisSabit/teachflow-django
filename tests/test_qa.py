"""Tests for lesson Q&A."""
from django.test import TestCase
from django.urls import reverse

from apps.learning.models import Enrollment, LessonAnswer, LessonQuestion
from tests.helpers import login_as, make_course, make_instructor, make_user
from tests.test_lessons import make_lesson, make_section


class LessonQATests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.lesson = make_lesson(
            make_section(course=make_course(instructor=self.instructor))
        )
        self.course = self.lesson.section.course
        self.student = make_user()
        Enrollment.objects.create(student=self.student, course=self.course)
        login_as(self.client, self.student)

    def ask_url(self):
        return reverse(
            "learning:ask_question", kwargs={"lesson_pk": self.lesson.pk}
        )

    def test_enrolled_student_can_ask(self):
        response = self.client.post(
            self.ask_url(), {"text": "What is a view?"}
        )
        self.assertRedirects(
            response, reverse("courses:lesson_detail", args=[self.lesson.pk])
        )
        question = LessonQuestion.objects.get(lesson=self.lesson)
        self.assertEqual(question.text, "What is a view?")
        self.assertEqual(question.student, self.student)

    def test_question_shows_on_the_lesson_page(self):
        LessonQuestion.objects.create(
            lesson=self.lesson, student=self.student, text="What is a view?"
        )
        response = self.client.get(
            reverse("courses:lesson_detail", args=[self.lesson.pk])
        )
        self.assertContains(response, "What is a view?")
        self.assertContains(response, "Waiting for the instructor")

    def test_non_enrolled_student_cannot_ask(self):
        login_as(self.client, make_user(username="outsider"))
        response = self.client.post(self.ask_url(), {"text": "Hello?"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(LessonQuestion.objects.exists())

    def test_instructor_can_answer(self):
        question = LessonQuestion.objects.create(
            lesson=self.lesson, student=self.student, text="What is a view?"
        )
        login_as(self.client, self.instructor)
        response = self.client.post(
            reverse(
                "learning:answer_question",
                kwargs={"question_pk": question.pk},
            ),
            {"text": "A view handles a request and returns a response."},
        )
        self.assertRedirects(
            response, reverse("courses:lesson_detail", args=[self.lesson.pk])
        )
        answer = LessonAnswer.objects.get(question=question)
        self.assertEqual(answer.instructor, self.instructor)
        response = self.client.get(
            reverse("courses:lesson_detail", args=[self.lesson.pk])
        )
        self.assertContains(response, "A view handles a request")

    def test_student_cannot_answer(self):
        question = LessonQuestion.objects.create(
            lesson=self.lesson, student=self.student, text="What is a view?"
        )
        response = self.client.post(
            reverse(
                "learning:answer_question",
                kwargs={"question_pk": question.pk},
            ),
            {"text": "I will answer it myself."},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(LessonAnswer.objects.exists())

    def test_other_instructor_cannot_answer(self):
        question = LessonQuestion.objects.create(
            lesson=self.lesson, student=self.student, text="What is a view?"
        )
        login_as(self.client, make_instructor(username="other-teacher"))
        response = self.client.post(
            reverse(
                "learning:answer_question",
                kwargs={"question_pk": question.pk},
            ),
            {"text": "Not my course."},
        )
        self.assertEqual(response.status_code, 403)

    def test_answering_twice_replaces_the_answer(self):
        question = LessonQuestion.objects.create(
            lesson=self.lesson, student=self.student, text="What is a view?"
        )
        login_as(self.client, self.instructor)
        url = reverse(
            "learning:answer_question", kwargs={"question_pk": question.pk}
        )
        self.client.post(url, {"text": "First answer."})
        self.client.post(url, {"text": "Better answer."})
        self.assertEqual(LessonAnswer.objects.count(), 1)
        self.assertEqual(
            LessonAnswer.objects.get(question=question).text, "Better answer."
        )
