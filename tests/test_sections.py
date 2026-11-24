"""Tests for course sections."""
from django.test import TestCase
from django.urls import reverse

from apps.courses.models import Course, Section
from tests.helpers import login_as, make_course, make_instructor


class SectionModelTests(TestCase):
    def test_sections_go_at_the_end_when_no_order_given(self):
        course = make_course()
        first = Section.objects.create(course=course, title="Getting started")
        second = Section.objects.create(course=course, title="Going deeper")
        self.assertEqual(first.order, 1)
        self.assertEqual(second.order, 2)

    def test_explicit_order_is_kept(self):
        course = make_course()
        section = Section.objects.create(course=course, title="Advanced", order=5)
        self.assertEqual(section.order, 5)

    def test_sections_order_by_their_order_field(self):
        course = make_course()
        Section.objects.create(course=course, title="Second", order=2)
        Section.objects.create(course=course, title="First", order=1)
        titles = list(course.sections.values_list("title", flat=True))
        self.assertEqual(titles, ["First", "Second"])


class SectionViewTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.other = make_instructor(username="other-teacher")
        self.course = make_course(instructor=self.instructor)
        login_as(self.client, self.instructor)

    def test_create_adds_a_section_to_my_course(self):
        response = self.client.post(
            reverse("courses:section_create", args=[self.course.pk]),
            {"title": "Getting started", "order": 0},
        )
        self.assertRedirects(
            response, reverse("courses:detail", args=[self.course.pk])
        )
        section = Section.objects.get(course=self.course)
        self.assertEqual(section.title, "Getting started")
        self.assertEqual(section.order, 1)

    def test_create_is_404_for_another_instructors_course(self):
        login_as(self.client, self.other)
        response = self.client.post(
            reverse("courses:section_create", args=[self.course.pk]),
            {"title": "Sneaky", "order": 0},
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Section.objects.filter(title="Sneaky").exists())

    def test_student_cannot_create_a_section(self):
        from tests.helpers import make_user

        login_as(self.client, make_user(username="student-y"))
        response = self.client.get(
            reverse("courses:section_create", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_edit_renames_my_section(self):
        section = Section.objects.create(course=self.course, title="Old")
        response = self.client.post(
            reverse("courses:section_edit", args=[section.pk]),
            {"title": "New", "order": 1},
        )
        self.assertRedirects(
            response, reverse("courses:detail", args=[self.course.pk])
        )
        section.refresh_from_db()
        self.assertEqual(section.title, "New")

    def test_delete_removes_my_section(self):
        section = Section.objects.create(course=self.course, title="Gone")
        response = self.client.post(
            reverse("courses:section_delete", args=[section.pk])
        )
        self.assertRedirects(
            response, reverse("courses:detail", args=[self.course.pk])
        )
        self.assertFalse(Section.objects.filter(pk=section.pk).exists())

    def test_detail_page_lists_sections_in_order(self):
        Section.objects.create(course=self.course, title="Second", order=2)
        Section.objects.create(course=self.course, title="First", order=1)
        response = self.client.get(
            reverse("courses:detail", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertLess(body.index("First"), body.index("Second"))
