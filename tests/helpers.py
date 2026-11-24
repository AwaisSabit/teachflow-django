"""Shared factories for TeachFlow tests.

Every helper builds a small, valid object with sensible defaults;
pass overrides for the fields a test cares about.
"""
import uuid

from django.contrib.auth import get_user_model

User = get_user_model()

TEST_PASSWORD = "LearnPass123!"


def _unique(prefix):
    """A short unique suffix, so calling a factory twice in one test
    never collides on a unique field."""
    return f"{prefix}-{uuid.uuid4().hex[:6]}"


def make_user(username=None, password=TEST_PASSWORD, **kwargs):
    """A student (the default role)."""
    if username is None:
        username = _unique("layla")
    kwargs.setdefault("email", f"{username}@example.com")
    return User.objects.create_user(username=username, password=password, **kwargs)


def make_instructor(username=None, password=TEST_PASSWORD, **kwargs):
    """An instructor, able to create courses."""
    if username is None:
        username = _unique("bilal")
    kwargs.setdefault("email", f"{username}@example.com")
    return User.objects.create_user(
        username=username,
        password=password,
        role=User.Role.INSTRUCTOR,
        **kwargs,
    )


def make_category(name=None, **kwargs):
    from apps.courses.models import Category

    if name is None:
        name = _unique("Python")
    kwargs.setdefault("description", f"Learn {name}.")
    return Category.objects.create(name=name, **kwargs)


def make_course(instructor=None, category=None, **kwargs):
    """A published course by default; pass status="draft" to change it."""
    from apps.courses.models import Course

    if instructor is None:
        instructor = make_instructor()
    if category is None:
        category = make_category()
    kwargs.setdefault("title", "Python for Beginners")
    kwargs.setdefault("subtitle", "From zero to your first program.")
    kwargs.setdefault("description", "A friendly first course in Python.")
    kwargs.setdefault("price", 0)
    kwargs.setdefault("status", Course.Status.PUBLISHED)
    return Course.objects.create(
        instructor=instructor, category=category, **kwargs
    )


def login_as(client, user, password=TEST_PASSWORD):
    """Log the test client in as this user; returns True when it worked."""
    return client.login(username=user.username, password=password)
