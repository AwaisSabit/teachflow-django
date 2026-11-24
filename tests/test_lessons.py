"""Tests for lessons."""
from django.test import TestCase
from django.urls import reverse

from apps.courses.models import Course, Lesson, Section
from tests.helpers import login_as, make_course, make_instructor, make_user


def make_section(course=None, **kwargs):
    if course is None:
        course = make_course()
    kwargs.setdefault("title", "Getting started")
    return Section.objects.create(course=course, **kwargs)


def make_lesson(section=None, **kwargs):
    if section is None:
        section = make_section()
    kwargs.setdefault("title", "Welcome")
    return Lesson.objects.create(section=section, **kwargs)


class LessonModelTests(TestCase):
    def test_lessons_go_at_the_end_when_no_order_given(self):
        section = make_section()
        first = make_lesson(section, title="One")
        second = make_lesson(section, title="Two")
        self.assertEqual(first.order, 1)
        self.assertEqual(second.order, 2)

    def test_youtube_watch_link_becomes_an_embed_link(self):
        lesson = make_lesson(
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        self.assertEqual(
            lesson.video_embed_url, "https://www.youtube.com/embed/dQw4w9WgXcQ"
        )

    def test_short_youtube_link_becomes_an_embed_link(self):
        lesson = make_lesson(video_url="https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual(
            lesson.video_embed_url, "https://www.youtube.com/embed/dQw4w9WgXcQ"
        )

    def test_other_video_links_are_used_as_they_are(self):
        lesson = make_lesson(video_url="https://example.com/video.mp4")
        self.assertEqual(lesson.video_embed_url, "https://example.com/video.mp4")

    def test_no_video_means_no_embed_url(self):
        lesson = make_lesson(video_url="")
        self.assertEqual(lesson.video_embed_url, "")

    def test_attachment_urls_split_lines(self):
        lesson = make_lesson(
            attachments="https://example.com/slides.pdf\n\nhttps://example.com/code.zip\n"
        )
        self.assertEqual(
            lesson.attachment_urls(),
            ["https://example.com/slides.pdf", "https://example.com/code.zip"],
        )


class LessonViewTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.section = make_section(course=make_course(instructor=self.instructor))
        login_as(self.client, self.instructor)

    def lesson_data(self, **overrides):
        data = {
            "title": "Welcome",
            "order": 0,
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "content": "Welcome to the course.",
            "attachments": "",
        }
        data.update(overrides)
        return data

    def test_create_adds_a_lesson_to_my_section(self):
        response = self.client.post(
            reverse("courses:lesson_create", args=[self.section.pk]),
            self.lesson_data(),
        )
        self.assertRedirects(
            response,
            reverse("courses:detail", args=[self.section.course.pk]),
        )
        lesson = Lesson.objects.get(section=self.section)
        self.assertEqual(lesson.title, "Welcome")
        self.assertEqual(lesson.order, 1)

    def test_create_is_404_for_another_instructors_section(self):
        login_as(self.client, make_instructor(username="other-teacher"))
        response = self.client.post(
            reverse("courses:lesson_create", args=[self.section.pk]),
            self.lesson_data(),
        )
        self.assertEqual(response.status_code, 404)

    def test_student_cannot_create_a_lesson(self):
        login_as(self.client, make_user(username="student-z"))
        response = self.client.get(
            reverse("courses:lesson_create", args=[self.section.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_edit_updates_my_lesson(self):
        lesson = make_lesson(self.section)
        response = self.client.post(
            reverse("courses:lesson_edit", args=[lesson.pk]),
            self.lesson_data(title="Welcome back"),
        )
        self.assertRedirects(
            response,
            reverse("courses:detail", args=[self.section.course.pk]),
        )
        lesson.refresh_from_db()
        self.assertEqual(lesson.title, "Welcome back")

    def test_delete_removes_my_lesson(self):
        lesson = make_lesson(self.section)
        response = self.client.post(
            reverse("courses:lesson_delete", args=[lesson.pk])
        )
        self.assertRedirects(
            response,
            reverse("courses:detail", args=[self.section.course.pk]),
        )
        self.assertFalse(Lesson.objects.filter(pk=lesson.pk).exists())

    def test_lesson_page_shows_video_content_and_attachments(self):
        lesson = make_lesson(
            self.section,
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            content="Welcome to the course.",
            attachments="https://example.com/slides.pdf",
        )
        response = self.client.get(
            reverse("courses:lesson_detail", args=[lesson.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "youtube.com/embed/dQw4w9WgXcQ")
        self.assertContains(response, "Welcome to the course.")
        self.assertContains(response, "https://example.com/slides.pdf")

    def test_lesson_of_a_draft_course_is_404_for_others(self):
        draft = make_course(status=Course.Status.DRAFT, title="Drafty")
        section = make_section(course=draft)
        lesson = make_lesson(section)
        login_as(self.client, make_user(username="curious-2"))
        response = self.client.get(
            reverse("courses:lesson_detail", args=[lesson.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_course_detail_lists_lessons_in_order(self):
        make_lesson(self.section, title="Second", order=2)
        make_lesson(self.section, title="First", order=1)
        response = self.client.get(
            reverse("courses:detail", args=[self.section.course.pk])
        )
        body = response.content.decode()
        self.assertLess(body.index("First"), body.index("Second"))
