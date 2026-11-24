"""Tests for the pass mark, retakes and the results page."""
from django.test import TestCase
from django.urls import reverse

from apps.learning.models import (
    Enrollment,
    QuizAttempt,
    has_passed,
    has_passed_all_quizzes,
)
from tests.helpers import login_as, make_course, make_instructor, make_user
from tests.test_lessons import make_lesson, make_section
from tests.test_quiz_taking import make_question
from tests.test_quizzes import make_quiz


class QuizResultsTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.lesson = make_lesson(
            make_section(course=make_course(instructor=self.instructor))
        )
        self.course = self.lesson.section.course
        self.quiz = make_quiz(self.lesson, pass_mark=70)
        self.q1, self.q1_choices = make_question(self.quiz)
        self.q2, self.q2_choices = make_question(
            self.quiz, text="What is Python?", correct="A language"
        )
        self.student = make_user()
        self.enrollment = Enrollment.objects.create(
            student=self.student, course=self.course
        )
        login_as(self.client, self.student)

    def take(self, right_first=True):
        data = {
            f"question_{self.q1.pk}": str(
                self.q1_choices[0 if right_first else 1].pk
            ),
            f"question_{self.q2.pk}": str(
                self.q2_choices[0 if right_first else 1].pk
            ),
        }
        return self.client.post(
            reverse(
                "learning:quiz_take", kwargs={"quiz_pk": self.quiz.pk}
            ),
            data,
        )

    def results_url(self):
        return reverse(
            "learning:quiz_results", kwargs={"quiz_pk": self.quiz.pk}
        )

    def test_results_page_lists_attempts_newest_first(self):
        self.take(right_first=False)  # 0%
        self.take(right_first=True)  # 100%
        response = self.client.get(self.results_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0%")
        self.assertContains(response, "100%")
        self.assertContains(response, "Failed")
        self.assertContains(response, "Passed")
        self.assertContains(response, "Take it again")

    def test_results_page_shows_best_score_and_passed(self):
        self.take(right_first=True)
        response = self.client.get(self.results_url())
        self.assertContains(response, "You have passed this quiz")
        self.assertContains(response, "Your best score is 100%")

    def test_results_page_before_any_attempt(self):
        response = self.client.get(self.results_url())
        self.assertContains(response, "have not taken this quiz yet")

    def test_retake_after_failing_is_allowed(self):
        self.take(right_first=False)
        response = self.take(right_first=True)
        self.assertEqual(
            QuizAttempt.objects.filter(
                quiz=self.quiz, student=self.student
            ).count(),
            2,
        )
        self.assertTrue(has_passed(self.quiz, self.student))

    def test_retake_after_passing_is_allowed(self):
        self.take(right_first=True)
        response = self.take(right_first=True)
        self.assertEqual(
            QuizAttempt.objects.filter(
                quiz=self.quiz, student=self.student
            ).count(),
            2,
        )

    def test_lesson_page_shows_passed_badge(self):
        self.take(right_first=True)
        response = self.client.get(
            reverse("courses:lesson_detail", args=[self.lesson.pk])
        )
        self.assertContains(response, "Quiz passed")
        self.assertContains(response, "My results")

    def test_non_enrolled_student_gets_a_403(self):
        login_as(self.client, make_user(username="outsider"))
        response = self.client.get(self.results_url())
        self.assertEqual(response.status_code, 403)

    def test_has_passed_all_quizzes(self):
        self.assertFalse(has_passed_all_quizzes(self.enrollment))
        self.take(right_first=True)
        self.assertTrue(has_passed_all_quizzes(self.enrollment))

    def test_course_with_no_quizzes_counts_as_passed(self):
        empty = make_course(title="No Quiz Course")
        enrollment = Enrollment.objects.create(
            student=self.student, course=empty
        )
        self.assertTrue(has_passed_all_quizzes(enrollment))
