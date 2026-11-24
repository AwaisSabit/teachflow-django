"""Admin for course categories and courses."""
from django.contrib import admin

from .models import Announcement, Category, Course, Lesson, Review, Section


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


class SectionInline(admin.TabularInline):
    model = Section
    extra = 0
    fields = ("title", "order")


class AnnouncementInline(admin.TabularInline):
    model = Announcement
    extra = 0
    fields = ("title", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "instructor",
        "status",
        "price",
        "level",
        "enrolment_count",
        "average_rating",
        "created_at",
    )
    list_filter = ("status", "level", "category", "instructor")
    search_fields = ("title", "subtitle", "description", "instructor__username")
    date_hierarchy = "created_at"
    inlines = [SectionInline, AnnouncementInline]

    def enrolment_count(self, course):
        return course.enrollments.count()

    enrolment_count.short_description = "Students"

    def average_rating(self, course):
        rating = course.average_rating()
        return f"{rating:.1f} / 5" if rating else "—"

    average_rating.short_description = "Rating"


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order")
    list_filter = ("course",)
    search_fields = ("title", "course__title")


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "order", "is_preview")
    list_filter = ("is_preview", "section__course")
    search_fields = ("title", "section__title")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("course", "student", "rating", "comment")
    list_filter = ("rating", "course")
    search_fields = ("course__title", "student__username", "comment")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "instructor", "created_at")
    list_filter = ("course",)
    search_fields = ("title", "body", "course__title")
    date_hierarchy = "created_at"
