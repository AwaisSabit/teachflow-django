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

    def average_rating(self):
        """Mean review rating, or None when nobody has reviewed yet."""
        from django.db.models import Avg

        return self.reviews.aggregate(Avg("rating"))["rating__avg"]

    def __str__(self):
        return self.title
