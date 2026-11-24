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

from .forms import LessonAnswerForm, LessonQuestionForm, QuizForm, QuizQuestionForm
from .models import (
    Enrollment,
    LessonCompletion,
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizChoice,
    QuizQuestion,
    Certificate,
    Certificate,
    LessonAnswer,
    LessonQuestion,
    best_attempt,
    has_passed,
    has_passed_all_quizzes,
    is_eligible_for_certificate,
    is_enrolled,
    next_lesson,
    progress_percent,
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
        from .notifications import notify_enrolled

        notify_enrolled(request.user, course)
        messages.success(request, f"You are now enrolled on “{course.title}”.")
    else:
        messages.info(request, "You are already enrolled on this course.")
    return redirect("courses:detail", pk=course.pk)


@login_required
def student_dashboard(request):
    """The student's learning: every course they are enrolled on,
    with its progress and the next lesson to continue with."""
    enrolments = (
        Enrollment.objects.filter(student=request.user)
        .select_related("course__category", "course__instructor")
        .order_by("-enrolled_at")
    )
    for enrolment in enrolments:
        enrolment.progress = progress_percent(enrolment)
        enrolment.next_lesson = next_lesson(enrolment)
        enrolment.eligible = is_eligible_for_certificate(enrolment)
    return render(
        request,
        "learning/student_dashboard.html",
        {"enrolments": enrolments},
    )


@instructor_required
def instructor_dashboard(request):
    """The instructor's own numbers: courses, students, enrolments,
    average ratings and earnings.

    Earnings are the money actually paid for a course — the price
    recorded on each order item, after any coupon discount.
    """
    from django.db.models import Avg, Count, Sum

    from apps.payments.models import OrderItem

    courses = (
        Course.objects.filter(instructor=request.user)
        .annotate(
            enrolment_count=Count("enrollments", distinct=True),
            avg_rating=Avg("reviews__rating"),
        )
        .order_by("-created_at")
    )
    course_ids = [course.pk for course in courses]
    revenue_by_course = dict(
        OrderItem.objects.filter(course_id__in=course_ids)
        .values("course_id")
        .annotate(total=Sum("price"))
        .values_list("course_id", "total")
    )
    for course in courses:
        course.revenue = revenue_by_course.get(course.pk, 0)
    total_students = Enrollment.objects.filter(
        course__instructor=request.user
    ).values("student").distinct().count()
    total_enrolments = Enrollment.objects.filter(
        course__instructor=request.user
    ).count()
    total_earnings = sum(revenue_by_course.values(), start=0)
    return render(
        request,
        "learning/instructor_dashboard.html",
        {
            "courses": courses,
            "total_students": total_students,
            "total_enrolments": total_enrolments,
            "total_earnings": total_earnings,
        },
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


@login_required
def quiz_results(request, quiz_pk):
    """The student's attempts at one quiz, newest first.

    Shows every attempt with its score and pass or fail, the best
    score so far, and whether the quiz is passed. A student may
    retake a quiz as many times as they like — the "Take it again"
    link goes back to the quiz.
    """
    quiz = get_object_or_404(
        Quiz.objects.select_related("lesson__section__course"), pk=quiz_pk
    )
    course = quiz.lesson.section.course
    if not is_enrolled(request.user, course):
        raise PermissionDenied("Enrol on this course to see your results.")
    attempts = QuizAttempt.objects.filter(
        quiz=quiz, student=request.user
    ).prefetch_related("answers__question")
    return render(
        request,
        "learning/quiz_results.html",
        {
            "quiz": quiz,
            "attempts": attempts,
            "best": best_attempt(quiz, request.user),
            "passed": has_passed(quiz, request.user),
        },
    )


@login_required
def certificate(request, course_pk):
    """The certificate page for one course.

    Only the enrolled student may see it, and only once they have
    finished every lesson and passed every quiz. Until then the
    page says plainly what is still missing. When the student
    qualifies, the certificate is created once and shown every
    time after.
    """
    course = get_object_or_404(Course, pk=course_pk)
    enrollment = Enrollment.objects.filter(
        student=request.user, course=course
    ).first()
    if enrollment is None:
        raise PermissionDenied("Enrol on this course to earn its certificate.")
    eligible = is_eligible_for_certificate(enrollment)
    cert = None
    if eligible:
        cert, created = Certificate.objects.get_or_create(enrollment=enrollment)
        if created:
            from .notifications import notify_certificate_earned

            notify_certificate_earned(request.user, course, cert)
    return render(
        request,
        "learning/certificate.html",
        {
            "course": course,
            "enrollment": enrollment,
            "eligible": eligible,
            "certificate": cert,
            "progress": progress_percent(enrollment),
            "quizzes_passed": has_passed_all_quizzes(enrollment),
        },
    )


@login_required
def ask_question(request, lesson_pk):
    """Ask the instructor a question about a lesson.

    Only enrolled students may ask, and only about lessons of
    courses they are enrolled on.
    """
    from apps.courses.models import Lesson

    lesson = get_object_or_404(
        Lesson.objects.select_related("section__course"), pk=lesson_pk
    )
    if not is_enrolled(request.user, lesson.section.course):
        raise PermissionDenied("Enrol on this course to ask questions.")
    if request.method == "POST":
        form = LessonQuestionForm(request.POST)
        if form.is_valid():
            LessonQuestion.objects.create(
                lesson=lesson,
                student=request.user,
                text=form.cleaned_data["text"],
            )
            messages.success(request, "Your question has been posted.")
    return redirect("courses:lesson_detail", pk=lesson.pk)


@login_required
def answer_question(request, question_pk):
    """Answer a student's question about a lesson.

    Only the instructor of the course may answer, and a question
    gets one answer.
    """
    question = get_object_or_404(
        LessonQuestion.objects.select_related(
            "lesson__section__course"
        ),
        pk=question_pk,
    )
    if question.lesson.section.course.instructor != request.user:
        raise PermissionDenied("Only the course instructor can answer.")
    if request.method == "POST":
        form = LessonAnswerForm(request.POST)
        if form.is_valid():
            LessonAnswer.objects.update_or_create(
                question=question,
                defaults={
                    "instructor": request.user,
                    "text": form.cleaned_data["text"],
                },
            )
            messages.success(request, "Your answer has been posted.")
    return redirect(
        "courses:lesson_detail", pk=question.lesson.pk
    )
