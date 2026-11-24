"""Course browsing, management and detail views.

Learners only ever see published courses in the catalogue. Every
management view needs an instructor, and every query for one course
is scoped to that instructor's own courses, so another instructor's
course simply does not exist for this user.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import instructor_required
from apps.learning.models import is_enrolled

from .forms import AnnouncementForm, CourseForm, LessonForm, ReviewForm, SectionForm
from .models import Announcement, Category, Course, Lesson, Review, Section


def browse(request):
    """The course catalogue: published courses, searchable and filterable.

    `q` searches title, subtitle and description; `category` narrows
    to one category slug; `level` narrows to one level; `price` is
    "free", "paid" or empty for all. Drafts and submitted courses
    never appear here.
    """
    courses = Course.objects.filter(status=Course.Status.PUBLISHED).select_related(
        "category", "instructor"
    )
    search_query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    level = request.GET.get("level", "").strip()
    price = request.GET.get("price", "").strip()

    if search_query:
        courses = courses.filter(
            Q(title__icontains=search_query)
            | Q(subtitle__icontains=search_query)
            | Q(description__icontains=search_query)
        )
    if category_slug:
        courses = courses.filter(category__slug=category_slug)
    if level in dict(Course.Level.choices):
        courses = courses.filter(level=level)
    if price == "free":
        courses = courses.filter(price=0)
    elif price == "paid":
        courses = courses.filter(price__gt=0)

    # Sorting: newest first is the default; a learner may also sort
    # by price or by title. An unknown value falls back to newest.
    sort = request.GET.get("sort", "newest").strip()
    if sort == "price_low":
        courses = courses.order_by("price", "-created_at")
    elif sort == "price_high":
        courses = courses.order_by("-price", "-created_at")
    elif sort == "title":
        courses = courses.order_by("title")
    else:
        sort = "newest"
        courses = courses.order_by("-created_at")

    # Ten courses per page; the page links keep every filter.
    paginator = Paginator(courses, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    kept = request.GET.copy()
    kept.pop("page", None)
    query_string = kept.urlencode()

    return render(
        request,
        "courses/browse.html",
        {
            "courses": page_obj,
            "page_obj": page_obj,
            "query_string": query_string,
            "categories": Category.objects.all(),
            "levels": Course.Level.choices,
            "q": search_query,
            "category": category_slug,
            "level": level,
            "price": price,
            "sort": sort,
        },
    )


def category_detail(request, slug):
    """One category: its description and its published courses."""
    category = get_object_or_404(Category, slug=slug)
    # Learners only ever see published courses here; drafts and
    # submitted courses stay invisible outside the instructor's pages.
    courses = category.courses.filter(status=Course.Status.PUBLISHED)
    paginator = Paginator(courses, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "courses/category_detail.html",
        {
            "category": category,
            "courses": page_obj,
            "page_obj": page_obj,
            "query_string": "",
        },
    )


def _get_own_course(request, pk):
    """Fetch one of the signed-in instructor's courses, or 404.

    Another instructor's course simply does not exist for this user —
    editing or deleting it answers with a 404, never the other
    instructor's data.
    """
    return get_object_or_404(Course, pk=pk, instructor=request.user)


@instructor_required
def my_courses(request):
    """The signed-in instructor's own courses, drafts included."""
    courses = Course.objects.filter(instructor=request.user).select_related(
        "category"
    )
    return render(request, "courses/my_courses.html", {"courses": courses})


@instructor_required
def course_create(request):
    """Create a course. It starts as a draft — publishing is a
    separate step, so nothing half-written ever reaches learners."""
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = request.user
            course.status = Course.Status.DRAFT
            course.save()
            messages.success(request, "Your course has been created as a draft.")
            return redirect("courses:my_courses")
    else:
        form = CourseForm()
    return render(request, "courses/form.html", {"form": form, "course": None})


@instructor_required
def course_edit(request, pk):
    """Edit one of the instructor's own courses."""
    course = _get_own_course(request, pk)
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Your course has been updated.")
            return redirect("courses:my_courses")
    else:
        form = CourseForm(instance=course)
    return render(request, "courses/form.html", {"form": form, "course": course})


@instructor_required
def course_delete(request, pk):
    """Delete one of the instructor's own courses, after a confirm page."""
    course = _get_own_course(request, pk)
    if request.method == "POST":
        course.delete()
        messages.success(request, "Your course has been deleted.")
        return redirect("courses:my_courses")
    return render(request, "courses/confirm_delete.html", {"course": course})


@instructor_required
def submit_for_review(request, pk):
    """Send a draft to be published. Only a draft can be submitted,
    and only by its own instructor."""
    course = _get_own_course(request, pk)
    if request.method == "POST":
        if course.status == Course.Status.DRAFT:
            course.status = Course.Status.SUBMITTED
            course.save()
            messages.success(
                request, "Your course has been submitted for publishing."
            )
        else:
            messages.error(request, "Only a draft can be submitted.")
    return redirect("courses:my_courses")


@instructor_required
def publish(request, pk):
    """Publish a submitted course, so learners can find and buy it.
    A draft cannot jump straight to published — it goes through
    submission first."""
    course = _get_own_course(request, pk)
    if request.method == "POST":
        if course.status == Course.Status.SUBMITTED:
            course.status = Course.Status.PUBLISHED
            course.save()
            messages.success(request, "Your course is now published.")
        else:
            messages.error(
                request, "Only a submitted course can be published."
            )
    return redirect("courses:my_courses")


@instructor_required
def withdraw(request, pk):
    """Take a published or submitted course back to draft, so it
    stops being visible to learners while the instructor reworks it."""
    course = _get_own_course(request, pk)
    if request.method == "POST":
        if course.status in {Course.Status.PUBLISHED, Course.Status.SUBMITTED}:
            course.status = Course.Status.DRAFT
            course.save()
            messages.success(request, "Your course is back to draft.")
        else:
            messages.error(request, "Only a published course can be withdrawn.")
    return redirect("courses:my_courses")


@instructor_required
def section_create(request, course_pk):
    """Add a section to one of the instructor's own courses."""
    course = _get_own_course(request, course_pk)
    if request.method == "POST":
        form = SectionForm(request.POST)
        if form.is_valid():
            section = form.save(commit=False)
            section.course = course
            section.save()
            messages.success(request, "Section added.")
            return redirect("courses:detail", pk=course.pk)
    else:
        form = SectionForm()
    return render(
        request,
        "courses/section_form.html",
        {"form": form, "course": course, "section": None},
    )


@instructor_required
def section_edit(request, pk):
    """Rename or reorder one of the instructor's own sections."""
    section = get_object_or_404(
        Section, pk=pk, course__instructor=request.user
    )
    if request.method == "POST":
        form = SectionForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            messages.success(request, "Section updated.")
            return redirect("courses:detail", pk=section.course.pk)
    else:
        form = SectionForm(instance=section)
    return render(
        request,
        "courses/section_form.html",
        {"form": form, "course": section.course, "section": section},
    )


@instructor_required
def section_delete(request, pk):
    """Delete one of the instructor's own sections (and its lessons)."""
    section = get_object_or_404(
        Section, pk=pk, course__instructor=request.user
    )
    if request.method == "POST":
        course_pk = section.course.pk
        section.delete()
        messages.success(request, "Section deleted.")
        return redirect("courses:detail", pk=course_pk)
    return render(
        request, "courses/section_confirm_delete.html", {"section": section}
    )


@instructor_required
def lesson_create(request, section_pk):
    """Add a lesson to one of the instructor's own sections."""
    section = get_object_or_404(
        Section, pk=section_pk, course__instructor=request.user
    )
    if request.method == "POST":
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.section = section
            lesson.save()
            messages.success(request, "Lesson added.")
            return redirect("courses:detail", pk=section.course.pk)
    else:
        form = LessonForm()
    return render(
        request,
        "courses/lesson_form.html",
        {"form": form, "section": section, "lesson": None},
    )


@instructor_required
def lesson_edit(request, pk):
    """Edit one of the instructor's own lessons."""
    lesson = get_object_or_404(
        Lesson, pk=pk, section__course__instructor=request.user
    )
    if request.method == "POST":
        form = LessonForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, "Lesson updated.")
            return redirect("courses:detail", pk=lesson.section.course.pk)
    else:
        form = LessonForm(instance=lesson)
    return render(
        request,
        "courses/lesson_form.html",
        {"form": form, "section": lesson.section, "lesson": lesson},
    )


@instructor_required
def lesson_delete(request, pk):
    """Delete one of the instructor's own lessons."""
    lesson = get_object_or_404(
        Lesson, pk=pk, section__course__instructor=request.user
    )
    if request.method == "POST":
        course_pk = lesson.section.course.pk
        lesson.delete()
        messages.success(request, "Lesson deleted.")
        return redirect("courses:detail", pk=course_pk)
    return render(
        request, "courses/lesson_confirm_delete.html", {"lesson": lesson}
    )


def course_detail(request, pk, preview=False):
    """One course: what it teaches, who teaches it, its curriculum.

    Published courses are open to everyone. A draft or submitted
    course is only visible to its own instructor — learners get a
    404, so unpublished work never leaks. With preview=True the
    page is rendered as a student sees it, for the instructor to
    check before publishing.
    """
    if request.user.is_authenticated:
        course = get_object_or_404(
            Course.objects.select_related("category", "instructor"),
            pk=pk,
        )
        if not course.is_published and course.instructor != request.user:
            raise Http404("No course matches the given query.")
    else:
        course = get_object_or_404(
            Course.objects.select_related("category", "instructor"),
            pk=pk,
            status=Course.Status.PUBLISHED,
        )
    enrolled = is_enrolled(request.user, course)
    my_review = None
    progress = 0
    if request.user.is_authenticated:
        my_review = Review.objects.filter(
            course=course, student=request.user
        ).first()
    if enrolled:
        from apps.learning.models import Enrollment, progress_percent

        enrollment = Enrollment.objects.filter(
            student=request.user, course=course
        ).first()
        progress = progress_percent(enrollment)
    recommendations = (
        Course.objects.filter(
            category=course.category, status=Course.Status.PUBLISHED
        )
        .exclude(pk=course.pk)
        .annotate(enrolment_count=Count("enrollments"))
        .order_by("-enrolment_count", "-created_at")[:4]
    )
    return render(
        request,
        "courses/detail.html",
        {
            "course": course,
            "is_enrolled": enrolled,
            "progress": progress,
            "reviews": course.reviews.select_related("student"),
            "average_rating": course.average_rating(),
            "my_review": my_review,
            "recommendations": recommendations,
            "preview": preview,
        },
    )


def lesson_detail(request, pk):
    """Watch a lesson: the video, the written content, attachments.

    Preview lessons are open to everyone. Any other lesson needs an
    enrolment — or the instructor themself. A lesson of an unpublished
    course is only visible to its instructor.
    """
    lesson = get_object_or_404(
        Lesson.objects.select_related("section__course__instructor"),
        pk=pk,
    )
    course = lesson.section.course
    if not course.is_published and (
        not request.user.is_authenticated or course.instructor != request.user
    ):
        raise Http404("No lesson matches the given query.")
    if (
        course.is_published
        and not lesson.is_preview
        and request.user != course.instructor
        and not is_enrolled(request.user, course)
    ):
        raise PermissionDenied(
            "Enrol on this course to watch this lesson."
        )
    enrolled = is_enrolled(request.user, course)
    is_complete = False
    quiz_passed = False
    if enrolled:
        from apps.learning.models import (
            Enrollment,
            LessonCompletion,
            has_passed,
        )

        enrollment = Enrollment.objects.filter(
            student=request.user, course=course
        ).first()
        is_complete = LessonCompletion.objects.filter(
            enrollment=enrollment, lesson=lesson
        ).exists()
        if hasattr(lesson, "quiz"):
            quiz_passed = has_passed(lesson.quiz, request.user)
    from apps.learning.forms import LessonAnswerForm, LessonQuestionForm

    questions = lesson.questions.select_related(
        "student", "answer__instructor"
    )
    return render(
        request,
        "courses/lesson_detail.html",
        {
            "lesson": lesson,
            "course": course,
            "is_enrolled": enrolled,
            "is_complete": is_complete,
            "quiz_passed": quiz_passed,
            "questions": questions,
            "question_form": LessonQuestionForm(),
            "answer_form": LessonAnswerForm(),
        },
    )


@login_required
def add_review(request, pk):
    """Rate a course, or update your earlier rating.

    Only enrolled students may review — someone who has never taken
    the course cannot rate it. One review per student per course:
    writing again updates the first review instead of adding another.
    """
    course = get_object_or_404(Course, pk=pk, status=Course.Status.PUBLISHED)
    if not is_enrolled(request.user, course):
        raise PermissionDenied("Enrol on this course to review it.")
    review = Review.objects.filter(course=course, student=request.user).first()
    if request.method == "POST":
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            review.course = course
            review.student = request.user
            review.save()
            messages.success(request, "Thank you — your review has been saved.")
            return redirect("courses:detail", pk=course.pk)
    else:
        form = ReviewForm(instance=review)
    return render(
        request,
        "courses/review_form.html",
        {"form": form, "course": course, "review": review},
    )


@instructor_required
def announcement_create(request, course_pk):
    """Post an announcement on one of the instructor's own courses."""
    course = get_object_or_404(Course, pk=course_pk, instructor=request.user)
    if request.method == "POST":
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.course = course
            announcement.instructor = request.user
            announcement.save()
            from apps.learning.notifications import notify_announcement

            notify_announcement(course, announcement)
            messages.success(request, "Announcement posted.")
    return redirect("courses:detail", pk=course.pk)


@instructor_required
def announcement_delete(request, announcement_pk):
    """Delete one of the instructor's own announcements."""
    announcement = get_object_or_404(
        Announcement, pk=announcement_pk, instructor=request.user
    )
    if request.method == "POST":
        course_pk = announcement.course.pk
        announcement.delete()
        messages.success(request, "Announcement deleted.")
        return redirect("courses:detail", pk=course_pk)
    return render(
        request,
        "courses/announcement_confirm_delete.html",
        {"announcement": announcement},
    )


@instructor_required
def course_preview(request, pk):
    """See one of the instructor's own courses as a student sees it.

    The page is the public course page: no edit buttons, no
    instructor tools, and enrolment shown as disabled. Drafts can
    be previewed too, so the instructor can check the page before
    submitting it for publishing.
    """
    course = get_object_or_404(Course, pk=pk, instructor=request.user)
    return course_detail(request, pk=pk, preview=True)
