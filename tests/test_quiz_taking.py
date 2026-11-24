"""Tests for taking a quiz with auto-marking."""
from django.test import TestCase
from django.urls import reverse

from apps.learning.models import (
    Enrollment,
    QuizAnswer,
    QuizAttempt,
    QuizChoice,
    QuizQuestion,
)
from tests.helpers import login_as, make_course, make_instructor, make_user
from tests.test_lessons import make_lesson, make_section
from tests.test_quizzes import make_quiz


def make_question(quiz, text="What is Django?", correct="A web framework"):
    question = QuizQuestion.objects.create(quiz=quiz, text=text)
    choices = [
        QuizChoice.objects.create(
            question=question, text=correct, is_correct=True
        ),
        QuizChoice.objects.create(question=question, text="A database"),
        QuizChoice.objects.create(question=question, text="A language"),
        QuizChoice.objects.create(question=question, text="A server"),
    ]
    return question, choices


class QuizTakingTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.lesson = make_lesson(
            make_section(course=make_course(instructor=self.instructor))
        )
        self.quiz = make_quiz(self.lesson, pass_mark=70)
        self.q1, self.q1_choices = make_question(self.quiz)
        self.q2, self.q2_choices = make_question(
            self.quiz, text="What is Python?", correct="A language"
        )
        self.student = make_user()
        Enrollment.objects.create(student=self.student, course=self.lesson.section.course)
        login_as(self.client, self.student)

    def take_url(self):
        return reverse(
            "learning:quiz_take", kwargs={"quiz_pk": self.quiz.pk}
        )

    def answers(self, q1_choice, q2_choice):
        return {
            f"question_{self.q1.pk}": str(q1_choice.pk),
            f"question_{self.q2.pk}": str(q2_choice.pk),
        }

    def test_all_correct_scores_a_hundred_and_passes(self):
        response = self.client.post(
            self.take_url(),
            self.answers(self.q1_choices[0], self.q2_choices[0]),
        )
        attempt = QuizAttempt.objects.get(
            quiz=self.quiz, student=self.student
        )
        self.assertRedirects(
            response,
            reverse("learning:quiz_result", args=[attempt.pk]),
        )
        self.assertEqual(attempt.score, 100)
        self.assertTrue(attempt.passed)

    def test_half_correct_fails_below_the_pass_mark(self):
        response = self.client.post(
            self.take_url(),
            self.answers(self.q1_choices[0], self.q2_choices[1]),
        )
        attempt = QuizAttempt.objects.get(
            quiz=self.quiz, student=self.student
        )
        self.assertEqual(attempt.score, 50)
        self.assertFalse(attempt.passed)
        response = self.client.get(
            reverse("learning:quiz_result", args=[attempt.pk])
        )
        self.assertContains(response, "Not yet")
        self.assertContains(response, "50%")

    def test_result_page_shows_each_answer(self):
        self.client.post(
            self.take_url(),
            self.answers(self.q1_choices[0], self.q2_choices[1]),
        )
        attempt = QuizAttempt.objects.get(
            quiz=self.quiz, student=self.student
        )
        response = self.client.get(
            reverse("learning:quiz_result", args=[attempt.pk])
        )
        self.assertContains(response, "What is Django?")
        self.assertContains(response, "correct")
        self.assertContains(response, "A language")
        self.assertContains(response, "Correct answer")

    def test_unanswered_question_counts_as_wrong(self):
        response = self.client.post(
            self.take_url(),
            {f"question_{self.q1.pk}": str(self.q1_choices[0].pk)},
        )
        attempt = QuizAttempt.objects.get(
            quiz=self.quiz, student=self.student
        )
        self.assertEqual(attempt.score, 50)
        answer = QuizAnswer.objects.get(
            attempt=attempt, question=self.q2
        )
        self.assertIsNone(answer.chosen_choice)
        self.assertFalse(answer.is_correct)

    def test_non_enrolled_student_gets_a_403(self):
        login_as(self.client, make_user(username="outsider"))
        response = self.client.get(self.take_url())
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(self.take_url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_another_student_cannot_see_my_result(self):
        self.client.post(
            self.take_url(),
            self.answers(self.q1_choices[0], self.q2_choices[0]),
        )
        attempt = QuizAttempt.objects.get(
            quiz=self.quiz, student=self.student
        )
        login_as(self.client, make_user(username="other-student"))
        response = self.client.get(
            reverse("learning:quiz_result", args=[attempt.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_lesson_page_offers_the_quiz_to_enrolled_students(self):
        response = self.client.get(
            reverse("courses:lesson_detail", args=[self.lesson.pk])
        )
        self.assertContains(response, "Take the quiz")
