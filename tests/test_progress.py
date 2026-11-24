"""Tests for lesson completion and per-course progress."""
from django.test import TestCase
from django.urls import reverse

from apps.learning.models import (
    Enrollment,
    LessonCompletion,
    progress_percent,
)
from tests.helpers import login_as, make_course, make_instructor, make_user
from tests.test_lessons import make_lesson, make_section


class ProgressTests(TestCase):
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

    def complete_url(self, lesson=None):
        return reverse(
            "learning:toggle_complete", args=[(lesson or self.lesson1).pk]
        )

    def test_marking_complete_creates_a_record(self):
        response = self.client.post(self.complete_url())
        self.assertRedirects(
            response, reverse("courses:lesson_detail", args=[self.lesson1.pk])
        )
        self.assertTrue(
            LessonCompletion.objects.filter(
                enrollment=self.enrollment, lesson=self.lesson1
            ).exists()
        )

    def test_marking_again_removes_the_record(self):
        self.client.post(self.complete_url())
        self.client.post(self.complete_url())
        self.assertFalse(
            LessonCompletion.objects.filter(
                enrollment=self.enrollment, lesson=self.lesson1
            ).exists()
        )

    def test_progress_is_zero_with_no_lessons_done(self):
        self.assertEqual(progress_percent(self.enrollment), 0)

    def test_progress_is_half_with_one_of_two_lessons(self):
        LessonCompletion.objects.create(
            enrollment=self.enrollment, lesson=self.lesson1
        )
        self.assertEqual(progress_percent(self.enrollment), 50)

    def test_progress_is_full_when_everything_is_done(self):
        LessonCompletion.objects.create(
            enrollment=self.enrollment, lesson=self.lesson1
        )
        LessonCompletion.objects.create(
            enrollment=self.enrollment, lesson=self.lesson2
        )
        self.assertEqual(progress_percent(self.enrollment), 100)

    def test_progress_is_zero_for_a_course_with_no_lessons(self):
        empty = make_course(title="Empty Course")
        enrollment = Enrollment.objects.create(
            student=self.student, course=empty
        )
        self.assertEqual(progress_percent(enrollment), 0)

    def test_non_enrolled_student_cannot_complete(self):
        other = make_user(username="outsider")
        login_as(self.client, other)
        response = self.client.post(self.complete_url())
        self.assertEqual(response.status_code, 403)

    def test_lesson_page_shows_complete_button_and_state(self):
        response = self.client.get(
            reverse("courses:lesson_detail", args=[self.lesson1.pk])
        )
        self.assertContains(response, "Mark as complete")
        LessonCompletion.objects.create(
            enrollment=self.enrollment, lesson=self.lesson1
        )
        response = self.client.get(
            reverse("courses:lesson_detail", args=[self.lesson1.pk])
        )
        self.assertContains(response, "Completed — mark as not complete")

    def test_detail_page_shows_a_progress_bar(self):
        LessonCompletion.objects.create(
            enrollment=self.enrollment, lesson=self.lesson1
        )
        response = self.client.get(
            reverse("courses:detail", args=[self.course.pk])
        )
        self.assertContains(response, "50%")
        self.assertContains(response, 'role="progressbar"')

    def test_get_does_not_change_completion(self):
        self.client.get(self.complete_url())
        self.assertFalse(
            LessonCompletion.objects.filter(
                enrollment=self.enrollment, lesson=self.lesson1
            ).exists()
        )
