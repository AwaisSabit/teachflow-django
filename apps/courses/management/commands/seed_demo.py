"""Seed demo data for TeachFlow.

Creates one demo instructor ("demo-teacher") and one demo student
("demo-student"), three categories, four courses with sections,
lessons and quizzes, enrolments and reviews, so a new developer can
see the app populated with a single command:

    python manage.py seed_demo

Safety rules, written down here because they matter:

* The command refuses to run when DEBUG is off, unless --force is
  given — demo data must never land in a real deployment by accident.
* Running it twice does not duplicate anything: every record is
  created with get_or_create keyed on its natural fields.
* --clear wipes the demo accounts first — only those two accounts
  and what belongs to them. Nobody else's data is touched.
* The demo passwords are development-only fixtures. They are printed
  here and in the README so a new developer can log in; change them
  before any real use.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.courses.models import Category, Course, Lesson, Review, Section
from apps.learning.models import (
    Enrollment,
    LessonCompletion,
    Quiz,
    QuizChoice,
    QuizQuestion,
)
from apps.payments.models import Coupon

DEMO_PASSWORD = "DemoPass123!"
DEMO_TEACHER = ("demo-teacher", "demo-teacher@example.com", "Demo Teacher")
DEMO_STUDENT = ("demo-student", "demo-student@example.com", "Demo Student")

DEMO_CATEGORIES = ["Programming", "Design", "Business"]

# (title, category, price, level, status, subtitle, outcomes, requirements)
DEMO_COURSES = [
    (
        "Python for Beginners",
        "Programming",
        "0",
        Course.Level.BEGINNER,
        Course.Status.PUBLISHED,
        "Learn Python from zero, with small exercises at every step.",
        "Write your first Python programs\nWork with variables, lists and loops\nRead and write files",
        "A computer with Python installed\nNo programming experience needed",
    ),
    (
        "Django in Practice",
        "Programming",
        "49.99",
        Course.Level.INTERMEDIATE,
        Course.Status.PUBLISHED,
        "Build real web apps with Django — models, views and templates.",
        "Build a complete Django app\nUse the admin to manage data\nDeploy a finished project",
        "Python for Beginners, or basic Python\nA computer with Python installed",
    ),
    (
        "UI Design Basics",
        "Design",
        "29.99",
        Course.Level.BEGINNER,
        Course.Status.PUBLISHED,
        "Colour, type and layout — the foundations of good interface design.",
        "Choose colours that work together\nPick type that reads well\nLay out a clean interface",
        "No design experience needed",
    ),
    (
        "Freelancing 101",
        "Business",
        "0",
        Course.Level.ALL,
        Course.Status.DRAFT,
        "Find clients, price your work and get paid on time.",
        "Find your first clients\nPrice a project fairly\nWrite a simple contract",
        "A skill you can sell",
    ),
]

# (course title, section title, [(lesson title, is_preview), ...])
DEMO_CURRICULUM = [
    (
        "Python for Beginners",
        "Getting started",
        [("What is Python?", True), ("Your first program", False)],
    ),
    (
        "Python for Beginners",
        "Working with data",
        [("Variables and types", False), ("Lists and loops", False)],
    ),
    (
        "Django in Practice",
        "Models and the admin",
        [("Your first model", True), ("The admin site", False)],
    ),
    (
        "Django in Practice",
        "Views and templates",
        [("Writing a view", False), ("Templates and context", False)],
    ),
    (
        "UI Design Basics",
        "Colour and type",
        [("Colour that works", True), ("Choosing type", False)],
    ),
    (
        "UI Design Basics",
        "Layout",
        [("Grids and spacing", False), ("A clean interface", False)],
    ),
    (
        "Freelancing 101",
        "Finding clients",
        [("Where clients look", True), ("Your first proposal", False)],
    ),
]

# (course title, question, [choices], correct index)
DEMO_QUIZZES = [
    (
        "Python for Beginners",
        "What is Python?",
        "What does print() do?",
        ["Shows text on the screen", "Deletes a file", "Starts a server", "Saves a picture"],
        0,
    ),
    (
        "Django in Practice",
        "Your first model",
        "Where do Django models live?",
        ["models.py", "views.py", "urls.py", "settings.py"],
        0,
    ),
    (
        "UI Design Basics",
        "Colour that works",
        "What is contrast?",
        ["The difference between light and dark", "A font size", "A grid", "A file format"],
        0,
    ),
]

# (course title, rating, comment) — from the demo student
DEMO_REVIEWS = [
    ("Python for Beginners", 5, "Clear, friendly and easy to follow."),
    ("Django in Practice", 4, "A solid next step after Python."),
]


class Command(BaseCommand):
    help = (
        "Create demo data: a demo instructor and student, three "
        "categories, four courses with sections, lessons and quizzes, "
        "enrolments and reviews. Refuses to run when DEBUG is off "
        "unless --force is given. Safe to run twice."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete the demo accounts first, then seed again.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow seeding even when DEBUG is off.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "DEBUG is off, so this command will not seed demo data "
                "here. Run it in development, or pass --force if you "
                "really mean it."
            )

        User = get_user_model()

        if options["clear"]:
            deleted, _ = User.objects.filter(
                username__in=[DEMO_TEACHER[0], DEMO_STUDENT[0]]
            ).delete()
            if deleted:
                self.stdout.write("Cleared the demo accounts.")
            else:
                self.stdout.write("No demo accounts to clear.")

        teacher = self._make_user(User, *DEMO_TEACHER, role="instructor")
        student = self._make_user(User, *DEMO_STUDENT, role="student")

        categories = self._seed_categories()
        courses = self._seed_courses(teacher, categories)
        self._seed_curriculum(courses)
        self._seed_quizzes(courses)
        self._seed_enrolments(student, courses)
        self._seed_reviews(student, courses)
        self._seed_coupon()

        self.stdout.write(
            f"Demo data ready: {Category.objects.count()} categories, "
            f"{Course.objects.count()} courses, "
            f"{Lesson.objects.count()} lessons, "
            f"{Enrollment.objects.filter(student=student).count()} enrolments "
            "for the demo student."
        )
        self.stdout.write(
            f"Log in as {DEMO_TEACHER[0]} or {DEMO_STUDENT[0]} "
            f"with password {DEMO_PASSWORD}."
        )

    def _make_user(self, User, username, email, display_name, role):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "display_name": display_name,
                "role": role,
            },
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
            self.stdout.write(f"Created demo user {username}.")
        else:
            self.stdout.write(
                f"Demo user {username} already exists — keeping it."
            )
        return user

    def _seed_categories(self):
        categories = {}
        for name in DEMO_CATEGORIES:
            category, _ = Category.objects.get_or_create(name=name)
            categories[name] = category
        return categories

    def _seed_courses(self, teacher, categories):
        courses = {}
        for title, category_name, price, level, status, subtitle, outcomes, requirements in DEMO_COURSES:
            course, _ = Course.objects.get_or_create(
                title=title,
                defaults={
                    "subtitle": subtitle,
                    "description": subtitle,
                    "price": price,
                    "level": level,
                    "language": "English",
                    "category": categories[category_name],
                    "instructor": teacher,
                    "status": status,
                    "what_you_will_learn": outcomes,
                    "requirements": requirements,
                },
            )
            courses[title] = course
        return courses

    def _seed_curriculum(self, courses):
        for course_title, section_title, lessons in DEMO_CURRICULUM:
            section, _ = Section.objects.get_or_create(
                course=courses[course_title], title=section_title
            )
            for lesson_title, is_preview in lessons:
                Lesson.objects.get_or_create(
                    section=section,
                    title=lesson_title,
                    defaults={
                        "content": f"In this lesson: {lesson_title}.",
                        "is_preview": is_preview,
                    },
                )

    def _seed_quizzes(self, courses):
        for course_title, lesson_title, question_text, choices, correct in DEMO_QUIZZES:
            lesson = Lesson.objects.get(
                section__course=courses[course_title], title=lesson_title
            )
            quiz, _ = Quiz.objects.get_or_create(
                lesson=lesson,
                defaults={"title": f"Check what you learned: {lesson_title}"},
            )
            question, _ = QuizQuestion.objects.get_or_create(
                quiz=quiz, text=question_text
            )
            for index, choice_text in enumerate(choices):
                QuizChoice.objects.get_or_create(
                    question=question,
                    text=choice_text,
                    defaults={"is_correct": index == correct},
                )

    def _seed_enrolments(self, student, courses):
        for title, course in courses.items():
            if course.status != Course.Status.PUBLISHED:
                continue
            enrollment, _ = Enrollment.objects.get_or_create(
                student=student, course=course
            )
            if title == "Python for Beginners":
                first_lesson = Lesson.objects.filter(
                    section__course=course
                ).order_by("section__order", "order", "id").first()
                if first_lesson is not None:
                    LessonCompletion.objects.get_or_create(
                        enrollment=enrollment, lesson=first_lesson
                    )

    def _seed_reviews(self, student, courses):
        for title, rating, comment in DEMO_REVIEWS:
            Review.objects.get_or_create(
                course=courses[title],
                student=student,
                defaults={"rating": rating, "comment": comment},
            )

    def _seed_coupon(self):
        now = timezone.now()
        Coupon.objects.get_or_create(
            code="LEARN20",
            defaults={
                "percent": 20,
                "scope": Coupon.Scope.SITE,
                "valid_from": now - timedelta(days=1),
                "valid_until": now + timedelta(days=365),
            },
        )
