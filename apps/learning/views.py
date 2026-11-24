"""Learning views: enrolment, dashboards and progress.

Enrolment is the front door to learning: a free course enrols with
one click; a paid course goes through the cart and checkout instead.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import instructor_required

from apps.courses.models import Course

from .forms import QuizForm, QuizQuestionForm
from .models import (
    Enrollment,
    LessonCompletion,
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizChoice,
    QuizQuestion,
    is_enrolled,
)


@login_required
def enrol(request, course_pk):
    """Enrol the signed-in user on a free course.

    A free course enrols with one click and never asks for payment.
    A paid course cannot be enrolled on directly — it goes through
    the cart and the simulated checkout, which create the enrolment
    when the order completes.
    """
    course = get_object_or_404(
        Course, pk=course_pk, status=Course.Status.PUBLISHED
    )
    if request.method != "POST":
        return redirect("courses:detail", pk=course.pk)
    if not course.is_free:
        messages.info(
            request,
            "This is a paid course — add it to your cart to buy it.",
        )
        return redirect("courses:detail", pk=course.pk)
    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user, course=course
    )
    if created:
        messages.success(request, f"You are now enrolled on “{course.title}”.")
    else:
        messages.info(request, "You are already enrolled on this course.")
    return redirect("courses:detail", pk=course.pk)


def student_dashboard(request):
    """Placeholder student dashboard."""
    return render(
        request,
        "coming_soon.html",
        {"title": "My learning", "message": "Your learning dashboard is coming soon."},
    )


def instructor_dashboard(request):
    """Placeholder instructor dashboard."""
    return render(
        request,
        "coming_soon.html",
        {"title": "Teach", "message": "Your instructor dashboard is coming soon."},
    )


@login_required
def toggle_complete(request, lesson_pk):
    """Mark a lesson complete — or unmark it again.

    Only an enrolled student may complete a lesson, and only a
    lesson of the course they are enrolled on. Completing the same
    lesson twice does nothing; unmarking removes the record.
    """
    from apps.courses.models import Lesson

    lesson = get_object_or_404(
        Lesson.objects.select_related("section__course"), pk=lesson_pk
    )
    course = lesson.section.course
    enrollment = Enrollment.objects.filter(
        student=request.user, course=course
    ).first()
    if enrollment is None:
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied("Enrol on this course to track your progress.")
    if request.method == "POST":
        completion, created = LessonCompletion.objects.get_or_create(
            enrollment=enrollment, lesson=lesson
        )
        if not created:
            completion.delete()
            messages.info(request, f"“{lesson.title}” marked as not complete.")
        else:
            messages.success(request, f"“{lesson.title}” marked as complete.")
    return redirect("courses:lesson_detail", pk=lesson.pk)


def _get_own_lesson(request, lesson_pk):
    """Fetch one lesson of the signed-in instructor's courses, or 404."""
    from apps.courses.models import Lesson

    return get_object_or_404(
        Lesson, pk=lesson_pk, section__course__instructor=request.user
    )


@instructor_required
def quiz_create(request, lesson_pk):
    """Add a quiz to one of the instructor's own lessons."""
    lesson = _get_own_lesson(request, lesson_pk)
    if hasattr(lesson, "quiz"):
        messages.info(request, "This lesson already has a quiz.")
        return redirect("courses:lesson_detail", pk=lesson.pk)
    if request.method == "POST":
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.lesson = lesson
            quiz.save()
            messages.success(request, "Quiz created — now add some questions.")
            return redirect("learning:quiz_manage", quiz_pk=quiz.pk)
    else:
        form = QuizForm()
    return render(
        request, "learning/quiz_form.html", {"form": form, "lesson": lesson}
    )


@instructor_required
def quiz_manage(request, quiz_pk):
    """One quiz: its questions, with a form to add another."""
    quiz = get_object_or_404(
        Quiz, pk=quiz_pk, lesson__section__course__instructor=request.user
    )
    if request.method == "POST":
        form = QuizQuestionForm(request.POST)
        if form.is_valid():
            question = QuizQuestion.objects.create(
                quiz=quiz, text=form.cleaned_data["text"]
            )
            correct = form.cleaned_data["correct"]
            for key in ("a", "b", "c", "d"):
                QuizChoice.objects.create(
                    question=question,
                    text=form.cleaned_data[f"choice_{key}"],
                    is_correct=(key == correct),
                )
            messages.success(request, "Question added.")
            return redirect("learning:quiz_manage", quiz_pk=quiz.pk)
    else:
        form = QuizQuestionForm()
    return render(
        request, "learning/quiz_manage.html", {"quiz": quiz, "form": form}
    )


@instructor_required
def quiz_delete_question(request, question_pk):
    """Delete one question from the instructor's own quiz."""
    question = get_object_or_404(
        QuizQuestion,
        pk=question_pk,
        quiz__lesson__section__course__instructor=request.user,
    )
    if request.method == "POST":
        quiz_pk = question.quiz.pk
        question.delete()
        messages.success(request, "Question deleted.")
        return redirect("learning:quiz_manage", quiz_pk=quiz_pk)
    return render(
        request, "learning/question_confirm_delete.html", {"question": question}
    )


@login_required
def quiz_take(request, quiz_pk):
    """Take a quiz: answer every question, get marked at once.

    Only enrolled students may take a quiz. Each question is a radio
    list of its choices; an unanswered question counts as wrong. The
    score is the share of correct answers, and the attempt passes
    when the score reaches the quiz's pass mark.
    """
    from django import forms

    quiz = get_object_or_404(
        Quiz.objects.prefetch_related("questions__choices"),
        pk=quiz_pk,
    )
    course = quiz.lesson.section.course
    if not is_enrolled(request.user, course):
        raise PermissionDenied("Enrol on this course to take its quizzes.")
    questions = list(quiz.questions.all())
    if not questions:
        messages.info(request, "This quiz has no questions yet.")
        return redirect("courses:lesson_detail", pk=quiz.lesson.pk)

    class QuizTakeForm(forms.Form):
        """One radio field per question, built from the quiz itself."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for question in questions:
                self.fields[f"question_{question.pk}"] = forms.ChoiceField(
                    label=question.text,
                    choices=[
                        (choice.pk, choice.text)
                        for choice in question.choices.all()
                    ],
                    widget=forms.RadioSelect,
                    required=False,
                )

    if request.method == "POST":
        form = QuizTakeForm(request.POST)
        if form.is_valid():
            correct = 0
            answers = []
            for question in questions:
                chosen_id = form.cleaned_data.get(f"question_{question.pk}")
                chosen = None
                if chosen_id:
                    chosen = QuizChoice.objects.filter(
                        pk=chosen_id, question=question
                    ).first()
                if chosen is not None and chosen.is_correct:
                    correct += 1
                answers.append((question, chosen))
            score = round(correct / len(questions) * 100)
            attempt = QuizAttempt.objects.create(
                quiz=quiz,
                student=request.user,
                score=score,
                passed=score >= quiz.pass_mark,
            )
            for question, chosen in answers:
                QuizAnswer.objects.create(
                    attempt=attempt, question=question, chosen_choice=chosen
                )
            return redirect("learning:quiz_result", attempt_pk=attempt.pk)
    else:
        form = QuizTakeForm()
    return render(
        request,
        "learning/quiz_take.html",
        {"quiz": quiz, "form": form, "questions": questions},
    )


@login_required
def quiz_result(request, attempt_pk):
    """One attempt's result: the score, pass or fail, and every
    answer with the right one shown."""
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("quiz__lesson__section__course"),
        pk=attempt_pk,
        student=request.user,
    )
    return render(request, "learning/quiz_result.html", {"attempt": attempt})
