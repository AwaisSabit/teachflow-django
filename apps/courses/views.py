"""Course browsing views.

Learners browse by category. The browse page lists every category;
a category page shows the category and, once courses exist, the
published courses inside it.
"""
from django.shortcuts import get_object_or_404, render

from .models import Category


def browse(request):
    """List every category, so learners can pick a topic to explore."""
    categories = Category.objects.all()
    return render(request, "courses/browse.html", {"categories": categories})


def category_detail(request, slug):
    """One category: its description and its published courses."""
    category = get_object_or_404(Category, slug=slug)
    # Learners only ever see published courses here; drafts and
    # submitted courses stay invisible outside the instructor's pages.
    courses = category.courses.filter(status=Course.Status.PUBLISHED)
    return render(
        request,
        "courses/category_detail.html",
        {"category": category, "courses": courses},
    )


from django.contrib import messages
from django.shortcuts import redirect

from apps.accounts.decorators import instructor_required

from .forms import CourseForm, SectionForm
from .models import Course, Section


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


def course_detail(request, pk):
    """One course: what it teaches, who teaches it, its curriculum.

    Published courses are open to everyone. A draft or submitted
    course is only visible to its own instructor — learners get a
    404, so unpublished work never leaks.
    """
    if request.user.is_authenticated:
        course = get_object_or_404(
            Course.objects.select_related("category", "instructor"),
            pk=pk,
        )
        if not course.is_published and course.instructor != request.user:
            from django.http import Http404

            raise Http404("No course matches the given query.")
    else:
        course = get_object_or_404(
            Course.objects.select_related("category", "instructor"),
            pk=pk,
            status=Course.Status.PUBLISHED,
        )
    return render(request, "courses/detail.html", {"course": course})


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
