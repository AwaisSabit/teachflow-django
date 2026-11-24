"""Tests for course announcements."""
from django.test import TestCase
from django.urls import reverse

from apps.courses.models import Announcement
from apps.learning.models import Enrollment
from tests.helpers import login_as, make_course, make_instructor, make_user


class AnnouncementTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.course = make_course(instructor=self.instructor)
        self.student = make_user()
        Enrollment.objects.create(student=self.student, course=self.course)
        login_as(self.client, self.instructor)

    def create_url(self):
        return reverse(
            "courses:announcement_create", args=[self.course.pk]
        )

    def test_instructor_can_post_an_announcement(self):
        response = self.client.post(
            self.create_url(),
            {"title": "New lesson this week", "body": "Lesson 5 is live."},
        )
        self.assertRedirects(
            response, reverse("courses:detail", args=[self.course.pk])
        )
        announcement = Announcement.objects.get(course=self.course)
        self.assertEqual(announcement.title, "New lesson this week")
        self.assertEqual(announcement.instructor, self.instructor)

    def test_enrolled_student_sees_announcements(self):
        Announcement.objects.create(
            course=self.course,
            instructor=self.instructor,
            title="New lesson this week",
            body="Lesson 5 is live.",
        )
        login_as(self.client, self.student)
        response = self.client.get(
            reverse("courses:detail", args=[self.course.pk])
        )
        self.assertContains(response, "New lesson this week")
        self.assertContains(response, "Lesson 5 is live.")

    def test_non_enrolled_visitor_does_not_see_announcements(self):
        Announcement.objects.create(
            course=self.course,
            instructor=self.instructor,
            title="Secret update",
            body="For students only.",
        )
        login_as(self.client, make_user(username="outsider"))
        response = self.client.get(
            reverse("courses:detail", args=[self.course.pk])
        )
        self.assertNotContains(response, "Secret update")

    def test_student_cannot_post(self):
        login_as(self.client, self.student)
        response = self.client.post(
            self.create_url(), {"title": "Hello", "body": "I am a student."}
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Announcement.objects.exists())

    def test_other_instructor_cannot_post(self):
        login_as(self.client, make_instructor(username="other-teacher"))
        response = self.client.post(
            self.create_url(), {"title": "Hello", "body": "Not my course."}
        )
        self.assertEqual(response.status_code, 404)

    def test_instructor_can_delete_an_announcement(self):
        announcement = Announcement.objects.create(
            course=self.course,
            instructor=self.instructor,
            title="Old news",
            body="Outdated.",
        )
        response = self.client.post(
            reverse(
                "courses:announcement_delete", args=[announcement.pk]
            )
        )
        self.assertRedirects(
            response, reverse("courses:detail", args=[self.course.pk])
        )
        self.assertFalse(
            Announcement.objects.filter(pk=announcement.pk).exists()
        )

    def test_announcements_show_newest_first(self):
        Announcement.objects.create(
            course=self.course,
            instructor=self.instructor,
            title="First post",
            body="Older.",
        )
        Announcement.objects.create(
            course=self.course,
            instructor=self.instructor,
            title="Second post",
            body="Newer.",
        )
        login_as(self.client, self.student)
        response = self.client.get(
            reverse("courses:detail", args=[self.course.pk])
        )
        content = response.content.decode()
        self.assertLess(
            content.index("Second post"), content.index("First post")
        )
