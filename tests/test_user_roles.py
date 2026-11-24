"""Tests for the custom user model and its roles."""
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserRoleTests(TestCase):
    def test_new_user_is_a_student_by_default(self):
        user = User.objects.create_user(username="layla", password="LearnPass123!")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_instructor)

    def test_instructor_role_unlocks_teaching(self):
        user = User.objects.create_user(
            username="bilal",
            password="TeachPass123!",
            role=User.Role.INSTRUCTOR,
        )
        self.assertEqual(user.role, User.Role.INSTRUCTOR)
        self.assertTrue(user.is_instructor)
        self.assertFalse(user.is_student)

    def test_display_name_falls_back_to_username(self):
        plain = User.objects.create_user(username="omar", password="LearnPass123!")
        self.assertEqual(str(plain), "omar")
        named = User.objects.create_user(
            username="sara",
            password="LearnPass123!",
            display_name="Sara Ahmed",
        )
        self.assertEqual(str(named), "Sara Ahmed")

    def test_bio_is_optional(self):
        user = User.objects.create_user(username="hina", password="LearnPass123!")
        self.assertEqual(user.bio, "")
