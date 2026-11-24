"""Tests for registration, login, logout and profile."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

REGISTER_URL = reverse("accounts:register")
LOGIN_URL = reverse("accounts:login")
LOGOUT_URL = reverse("accounts:logout")
PROFILE_URL = reverse("accounts:profile")
HOME_URL = reverse("home")

GOOD_PASSWORD = "LearnPass123!"


def registration_data(**overrides):
    data = {
        "username": "layla",
        "email": "layla@example.com",
        "display_name": "Layla Khan",
        "role": "student",
        "password1": GOOD_PASSWORD,
        "password2": GOOD_PASSWORD,
    }
    data.update(overrides)
    return data


class RegistrationTests(TestCase):
    def test_register_page_loads(self):
        response = self.client.get(REGISTER_URL)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_registration_creates_student_and_signs_them_in(self):
        response = self.client.post(REGISTER_URL, registration_data())
        self.assertRedirects(response, HOME_URL)
        user = User.objects.get(username="layla")
        self.assertEqual(user.email, "layla@example.com")
        self.assertEqual(user.display_name, "Layla Khan")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(user.check_password(GOOD_PASSWORD))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_registration_as_instructor_sets_the_role(self):
        response = self.client.post(
            REGISTER_URL, registration_data(role="instructor")
        )
        self.assertRedirects(response, HOME_URL)
        user = User.objects.get(username="layla")
        self.assertTrue(user.is_instructor)

    def test_registration_needs_matching_passwords(self):
        response = self.client.post(
            REGISTER_URL, registration_data(password2="Different123!")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="layla").exists())

    def test_registration_needs_an_email(self):
        response = self.client.post(REGISTER_URL, registration_data(email=""))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="layla").exists())

    def test_signed_in_user_is_sent_home_from_register(self):
        User.objects.create_user(username="layla", password=GOOD_PASSWORD)
        self.client.login(username="layla", password=GOOD_PASSWORD)
        response = self.client.get(REGISTER_URL)
        self.assertRedirects(response, HOME_URL)


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="layla", password=GOOD_PASSWORD
        )

    def test_login_page_loads(self):
        response = self.client.get(LOGIN_URL)
        self.assertEqual(response.status_code, 200)

    def test_login_signs_the_user_in(self):
        response = self.client.post(
            LOGIN_URL, {"username": "layla", "password": GOOD_PASSWORD}
        )
        self.assertRedirects(response, HOME_URL)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_wrong_password_does_not_sign_in(self):
        response = self.client.post(
            LOGIN_URL, {"username": "layla", "password": "WrongPass123!"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_signs_the_user_out(self):
        self.client.login(username="layla", password=GOOD_PASSWORD)
        response = self.client.get(LOGOUT_URL)
        self.assertRedirects(response, HOME_URL)
        self.assertNotIn("_auth_user_id", self.client.session)


class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="layla",
            password=GOOD_PASSWORD,
            display_name="Layla Khan",
            role=User.Role.INSTRUCTOR,
        )
        self.client.login(username="layla", password=GOOD_PASSWORD)

    def test_profile_page_shows_role_and_bio(self):
        response = self.client.get(PROFILE_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Instructor")
        self.assertContains(response, "Layla Khan")

    def test_profile_update_saves_display_name_email_and_bio(self):
        response = self.client.post(
            PROFILE_URL,
            {
                "display_name": "Layla K",
                "email": "layla.k@example.com",
                "bio": "Python teacher with ten years of experience.",
            },
        )
        self.assertRedirects(response, PROFILE_URL)
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, "Layla K")
        self.assertEqual(self.user.email, "layla.k@example.com")
        self.assertIn("ten years", self.user.bio)

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(PROFILE_URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn(LOGIN_URL, response["Location"])
