"""Learning models: enrolment and progress.

An enrolment is a student taking a course. Lesson completion and
quizzes hang off the enrolment, so progress is always per student,
per course.
"""
from django.conf import settings
from django.db import models


class Enrollment(models.Model):
    """A student enrolled on a course."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, related_name="enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.student.username} on {self.course.title}"


def is_enrolled(user, course):
    """True when this signed-in user is enrolled on this course."""
    if not user.is_authenticated:
        return False
    return Enrollment.objects.filter(student=user, course=course).exists()


class LessonCompletion(models.Model):
    """One lesson finished by one student, inside one enrolment."""

    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="completions"
    )
    lesson = models.ForeignKey(
        "courses.Lesson", on_delete=models.CASCADE, related_name="completions"
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("enrollment", "lesson")
        ordering = ["completed_at"]

    def __str__(self):
        return f"{self.enrollment.student.username} finished {self.lesson.title}"


def progress_percent(enrollment):
    """How much of the course this enrolment has finished, 0–100.

    A course with no lessons yet is 0% — there is nothing to finish.
    """
    from apps.courses.models import Lesson

    total = Lesson.objects.filter(section__course=enrollment.course).count()
    if total == 0:
        return 0
    done = enrollment.completions.count()
    return round(done / total * 100)
