"""Tests for quiz creation by instructors."""
from django.test import TestCase
from django.urls import reverse

from apps.learning.models import Quiz, QuizChoice, QuizQuestion
from tests.helpers import login_as, make_course, make_instructor, make_user
from tests.test_lessons import make_lesson, make_section


def make_quiz(lesson=None, **kwargs):
    if lesson is None:
        lesson = make_lesson()
    kwargs.setdefault("title", "Check what you learned")
    return Quiz.objects.create(lesson=lesson, **kwargs)


def question_data(**overrides):
    data = {
        "text": "What does Django stand for?",
        "choice_a": "A web framework",
        "choice_b": "A database",
        "choice_c": "A language",
        "choice_d": "A server",
        "correct": "a",
    }
    data.update(overrides)
    return data


class QuizModelTests(TestCase):
    def test_quiz_belongs_to_one_lesson(self):
        lesson = make_lesson()
        quiz = make_quiz(lesson)
        self.assertEqual(lesson.quiz, quiz)
        self.assertEqual(quiz.pass_mark, 70)

    def test_questions_order_themselves(self):
        quiz = make_quiz()
        second = QuizQuestion.objects.create(quiz=quiz, text="Second")
        first = QuizQuestion.objects.create(quiz=quiz, text="First")
        self.assertEqual(first.order, 2)
        self.assertEqual(second.order, 1)
        self.assertEqual(
            list(quiz.questions.values_list("text", flat=True)),
            ["Second", "First"],
        )


class QuizCreateTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.lesson = make_lesson(
            make_section(course=make_course(instructor=self.instructor))
        )
        login_as(self.client, self.instructor)

    def test_instructor_can_create_a_quiz_for_their_lesson(self):
        response = self.client.post(
            reverse("learning:quiz_create", args=[self.lesson.pk]),
            {"title": "Check what you learned", "pass_mark": 70},
        )
        quiz = Quiz.objects.get(lesson=self.lesson)
        self.assertRedirects(
            response, reverse("learning:quiz_manage", kwargs={"quiz_pk": quiz.pk})
        )
        self.assertEqual(quiz.title, "Check what you learned")

    def test_pass_mark_must_be_between_one_and_a_hundred(self):
        response = self.client.post(
            reverse("learning:quiz_create", args=[self.lesson.pk]),
            {"title": "Bad quiz", "pass_mark": 150},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Quiz.objects.filter(lesson=self.lesson).exists())

    def test_second_quiz_for_the_same_lesson_is_refused(self):
        make_quiz(self.lesson)
        response = self.client.post(
            reverse("learning:quiz_create", args=[self.lesson.pk]),
            {"title": "Another quiz", "pass_mark": 70},
        )
        self.assertRedirects(
            response, reverse("courses:lesson_detail", args=[self.lesson.pk])
        )
        self.assertEqual(Quiz.objects.filter(lesson=self.lesson).count(), 1)

    def test_student_cannot_create_a_quiz(self):
        login_as(self.client, make_user(username="student-q"))
        response = self.client.get(
            reverse("learning:quiz_create", args=[self.lesson.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_other_instructor_cannot_create_a_quiz_on_my_lesson(self):
        login_as(self.client, make_instructor(username="other-teacher"))
        response = self.client.get(
            reverse("learning:quiz_create", args=[self.lesson.pk])
        )
        self.assertEqual(response.status_code, 404)


class QuizQuestionTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.quiz = make_quiz(
            make_lesson(
                make_section(course=make_course(instructor=self.instructor))
            )
        )
        login_as(self.client, self.instructor)

    def test_add_question_creates_four_choices_with_one_correct(self):
        response = self.client.post(
            reverse("learning:quiz_manage", kwargs={"quiz_pk": self.quiz.pk}),
            question_data(),
        )
        self.assertRedirects(
            response, reverse("learning:quiz_manage", kwargs={"quiz_pk": self.quiz.pk})
        )
        question = QuizQuestion.objects.get(quiz=self.quiz)
        self.assertEqual(question.text, "What does Django stand for?")
        choices = list(question.choices.all())
        self.assertEqual(len(choices), 4)
        correct = [c for c in choices if c.is_correct]
        self.assertEqual(len(correct), 1)
        self.assertEqual(correct[0].text, "A web framework")

    def test_manage_page_lists_questions(self):
        question = QuizQuestion.objects.create(
            quiz=self.quiz, text="What is Django?"
        )
        QuizChoice.objects.create(
            question=question, text="A web framework", is_correct=True
        )
        response = self.client.get(
            reverse("learning:quiz_manage", kwargs={"quiz_pk": self.quiz.pk})
        )
        self.assertContains(response, "What is Django?")
        self.assertContains(response, "A web framework")

    def test_delete_question(self):
        question = QuizQuestion.objects.create(quiz=self.quiz, text="Gone?")
        response = self.client.post(
            reverse("learning:quiz_delete_question", args=[question.pk])
        )
        self.assertRedirects(
            response, reverse("learning:quiz_manage", kwargs={"quiz_pk": self.quiz.pk})
        )
        self.assertFalse(QuizQuestion.objects.filter(pk=question.pk).exists())

    def test_student_cannot_manage_a_quiz(self):
        login_as(self.client, make_user(username="student-q"))
        response = self.client.get(
            reverse("learning:quiz_manage", kwargs={"quiz_pk": self.quiz.pk})
        )
        self.assertEqual(response.status_code, 403)
