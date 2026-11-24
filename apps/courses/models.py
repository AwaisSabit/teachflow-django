"""Course categories and courses.

A category groups courses ("Python", "Design", "Business"). Courses
are published by instructors and bought by students; sections and
lessons hang off a course, and reviews, enrolments and orders all
point at it. Only published courses are ever shown to learners —
drafts and submitted courses stay invisible outside the instructor's
own pages.
"""
from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    """A topic area courses belong to, such as Python or Design."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Course(models.Model):
    """A course an instructor teaches.

    Status drives the publishing workflow: an instructor creates a
    course as a draft, submits it for publishing, and it becomes
    visible to learners once published. A course with no price is
    free — anyone enrolled can learn it without a checkout.
    """

    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        ALL = "all", "All levels"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted for publishing"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    description = models.TextField()
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="0 means the course is free.",
    )
    level = models.CharField(
        max_length=20, choices=Level.choices, default=Level.ALL
    )
    language = models.CharField(max_length=50, default="English")
    thumbnail_url = models.URLField(
        blank=True,
        help_text="A link to the course cover image; a placeholder is used when empty.",
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="courses"
    )
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="courses_taught",
        limit_choices_to={"role": "instructor"},
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    what_you_will_learn = models.TextField(
        blank=True,
        help_text="One learning outcome per line; shown on the course page.",
    )
    requirements = models.TextField(
        blank=True,
        help_text="One requirement per line; shown on the course page.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_free(self):
        return self.price == 0

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED

    def learning_outcomes(self):
        """The what-you-will-learn lines, one per line."""
        return [line.strip() for line in self.what_you_will_learn.splitlines() if line.strip()]

    def requirement_lines(self):
        return [line.strip() for line in self.requirements.splitlines() if line.strip()]

    def section_count(self):
        """How many sections the course has."""
        return self.sections.count()

    def lesson_count(self):
        """How many lessons the course has, across all sections."""
        return Lesson.objects.filter(section__course=self).count()

    def preview_lesson(self):
        """The first lesson marked as a free preview, or None.

        Preview lessons can be watched without enrolling, so learners
        can try the course before they buy it.
        """
        return (
            Lesson.objects.filter(section__course=self, is_preview=True)
            .order_by("section__order", "order")
            .first()
        )

    def average_rating(self):
        """Mean review rating, or None when nobody has reviewed yet."""
        from django.db.models import Avg

        return self.reviews.aggregate(Avg("rating"))["rating__avg"]

    def __str__(self):
        return self.title


class Section(models.Model):
    """A chapter of a course, holding lessons in order.

    Sections are ordered within their course; a section with no
    order given goes at the end, after its siblings.
    """

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="sections"
    )
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(
        default=0,
        help_text="Leave as 0 to put this section at the end.",
    )

    class Meta:
        ordering = ["order", "id"]

    def save(self, *args, **kwargs):
        if not self.order:
            last = (
                Section.objects.filter(course=self.course)
                .order_by("-order")
                .values_list("order", flat=True)
                .first()
            )
            self.order = (last or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.course.title} — {self.title}"


class Lesson(models.Model):
    """One lesson inside a section.

    A lesson teaches with a video (embedded from a URL the instructor
    provides — TeachFlow hosts no video itself), written content, and
    an optional list of attachment links. Lessons are ordered inside
    their section; one with no order given goes at the end.
    """

    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="lessons"
    )
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(
        default=0,
        help_text="Leave as 0 to put this lesson at the end.",
    )
    video_url = models.URLField(
        blank=True,
        help_text="A link to the lesson video (for example a YouTube link).",
    )
    content = models.TextField(
        blank=True, help_text="Written lesson content, shown under the video."
    )
    attachments = models.TextField(
        blank=True,
        help_text="One attachment link per line.",
    )
    is_preview = models.BooleanField(
        default=False,
        help_text="Preview lessons can be watched without enrolling.",
    )

    class Meta:
        ordering = ["order", "id"]

    def save(self, *args, **kwargs):
        if not self.order:
            last = (
                Lesson.objects.filter(section=self.section)
                .order_by("-order")
                .values_list("order", flat=True)
                .first()
            )
            self.order = (last or 0) + 1
        super().save(*args, **kwargs)

    @property
    def video_embed_url(self):
        """The URL to embed in a player.

        YouTube watch links become embed links; anything else is
        used as it is.
        """
        from urllib.parse import parse_qs, urlparse

        if not self.video_url:
            return ""
        parsed = urlparse(self.video_url)
        if "youtube.com" in parsed.netloc and parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
            if video_id:
                return f"https://www.youtube.com/embed/{video_id}"
        if parsed.netloc in {"youtu.be"}:
            video_id = parsed.path.lstrip("/")
            if video_id:
                return f"https://www.youtube.com/embed/{video_id}"
        return self.video_url

    def attachment_urls(self):
        """The attachment links, one per line."""
        return [line.strip() for line in self.attachments.splitlines() if line.strip()]

    def __str__(self):
        return f"{self.section.course.title} — {self.title}"
