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
    """One category: its description and its published courses.

    The Course model lands in the next commit, so for now the page
    shows the category and an honest empty state.
    """
    category = get_object_or_404(Category, slug=slug)
    courses = []
    return render(
        request,
        "courses/category_detail.html",
        {"category": category, "courses": courses},
    )


from django.contrib import messages
from django.shortcuts import redirect

from apps.accounts.decorators import instructor_required

from .forms import CourseForm
from .models import Course


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
