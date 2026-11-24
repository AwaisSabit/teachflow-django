"""Admin for enrolments, quizzes and certificates."""
from django.contrib import admin

from .models import (
    Certificate,
    Enrollment,
    LessonAnswer,
    LessonCompletion,
    LessonQuestion,
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizChoice,
    QuizQuestion,
)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "progress", "enrolled_at")
    list_filter = ("course", "enrolled_at")
    search_fields = ("student__username", "course__title")
    date_hierarchy = "enrolled_at"

    def progress(self, enrollment):
        from .models import progress_percent

        return f"{progress_percent(enrollment)}%"

    progress.short_description = "Progress"


@admin.register(LessonCompletion)
class LessonCompletionAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "lesson", "completed_at")
    list_filter = ("lesson__section__course",)
    search_fields = ("enrollment__student__username", "lesson__title")


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 0
    fields = ("text", "order")


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson", "pass_mark", "question_count")
    list_filter = ("lesson__section__course",)
    search_fields = ("title", "lesson__title")
    inlines = [QuizQuestionInline]

    def question_count(self, quiz):
        return quiz.questions.count()

    question_count.short_description = "Questions"


class QuizChoiceInline(admin.TabularInline):
    model = QuizChoice
    extra = 0


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "quiz", "order")
    list_filter = ("quiz",)
    search_fields = ("text",)
    inlines = [QuizChoiceInline]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("quiz", "student", "score", "passed", "created_at")
    list_filter = ("passed", "quiz")
    search_fields = ("student__username", "quiz__title")
    date_hierarchy = "created_at"


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("certificate_number", "enrollment", "issued_at")
    search_fields = ("certificate_number", "enrollment__student__username")
    date_hierarchy = "issued_at"


@admin.register(LessonQuestion)
class LessonQuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "lesson", "student", "created_at")
    list_filter = ("lesson__section__course",)
    search_fields = ("text", "student__username")


@admin.register(LessonAnswer)
class LessonAnswerAdmin(admin.ModelAdmin):
    list_display = ("question", "instructor", "created_at")
    search_fields = ("text", "instructor__username")
