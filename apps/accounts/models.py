"""Custom user model for TeachFlow.

Defined before the first migration, so it can be changed later only
via a migration — never swap AUTH_USER_MODEL after data exists.
Every user is a student by default; an instructor is a user whose
role is "instructor", which unlocks teaching: creating courses and
seeing the instructor dashboard.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A learner or a teacher, with an optional display name and bio."""

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        INSTRUCTOR = "instructor", "Instructor"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        help_text="Students learn; instructors teach and manage courses.",
    )
    display_name = models.CharField(max_length=150, blank=True)
    bio = models.TextField(
        blank=True,
        help_text="Shown on the instructor bio on course pages.",
    )

    @property
    def is_instructor(self):
        """True when this user may teach — create courses and see the
        instructor dashboard."""
        return self.role == self.Role.INSTRUCTOR

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    def __str__(self):
        return self.display_name or self.username
