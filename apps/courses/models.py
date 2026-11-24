"""Course categories.

A category groups courses ("Python", "Design", "Business"). The
Course model itself lands in the next commit; this one only creates
the categories learners browse by.
"""
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
