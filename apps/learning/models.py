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


class Quiz(models.Model):
    """A quiz attached to one lesson.

    A quiz has a pass mark (70% by default). A student passes by
    answering at least that share of its questions correctly.
    """

    lesson = models.OneToOneField(
        "courses.Lesson", on_delete=models.CASCADE, related_name="quiz"
    )
    title = models.CharField(max_length=200)
    pass_mark = models.PositiveSmallIntegerField(
        default=70,
        help_text="The percentage of correct answers needed to pass.",
    )

    def __str__(self):
        return f"Quiz: {self.title}"


class QuizQuestion(models.Model):
    """One multiple-choice question inside a quiz."""

    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="questions"
    )
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def save(self, *args, **kwargs):
        if not self.order:
            last = (
                QuizQuestion.objects.filter(quiz=self.quiz)
                .order_by("-order")
                .values_list("order", flat=True)
                .first()
            )
            self.order = (last or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.text[:60]


class QuizChoice(models.Model):
    """One answer option for a question. Exactly one per question is
    the correct answer."""

    question = models.ForeignKey(
        QuizQuestion, on_delete=models.CASCADE, related_name="choices"
    )
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class QuizAttempt(models.Model):
    """One student's attempt at a quiz, with its score."""

    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="attempts"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
    )
    score = models.PositiveSmallIntegerField(
        help_text="The percentage of questions answered correctly."
    )
    passed = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.username} scored {self.score}% on {self.quiz.title}"


class QuizAnswer(models.Model):
    """One answer inside an attempt: what the student picked."""

    attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    chosen_choice = models.ForeignKey(
        QuizChoice, on_delete=models.SET_NULL, null=True, blank=True
    )

    @property
    def is_correct(self):
        return self.chosen_choice is not None and self.chosen_choice.is_correct


def best_attempt(quiz, student):
    """The student's best attempt at a quiz, or None."""
    return (
        QuizAttempt.objects.filter(quiz=quiz, student=student)
        .order_by("-score", "-created_at")
        .first()
    )


def has_passed(quiz, student):
    """True when the student has passed this quiz at least once."""
    return QuizAttempt.objects.filter(
        quiz=quiz, student=student, passed=True
    ).exists()


def has_passed_all_quizzes(enrollment):
    """True when the student passed every quiz in the course.

    A course with no quizzes counts as passed — there is nothing
    to pass. This is what the certificate checks.
    """
    from apps.courses.models import Lesson

    quizzes = Quiz.objects.filter(
        lesson__section__course=enrollment.course
    )
    if not quizzes.exists():
        return True
    return all(
        has_passed(quiz, enrollment.student) for quiz in quizzes
    )
