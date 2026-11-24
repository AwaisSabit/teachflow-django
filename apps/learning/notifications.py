"""Email notifications for TeachFlow.

In development the console backend prints these messages instead of
sending them, so nothing leaves the machine. In production the SMTP
settings in prod.py send them for real. A notification never breaks
the action it follows — if mail is misconfigured, the enrolment,
certificate or announcement still goes through.
"""
from django.core.mail import send_mail

FROM = "TeachFlow <noreply@teachflow.example>"


def _send(subject, body, recipient):
    if not recipient:
        return
    send_mail(subject, body, FROM, [recipient], fail_silently=True)


def notify_enrolled(student, course):
    """Tell a student they are enrolled on a course."""
    _send(
        f"You are enrolled on “{course.title}”",
        (
            f"Hi {student.display_name or student.username},\n\n"
            f"You are now enrolled on “{course.title}” "
            f"with {course.instructor.display_name or course.instructor.username}. "
            "You can start learning right away.\n\n"
            "Happy learning,\nThe TeachFlow team"
        ),
        student.email,
    )


def notify_certificate_earned(student, course, certificate):
    """Tell a student they earned a certificate."""
    _send(
        f"You earned a certificate for “{course.title}”",
        (
            f"Hi {student.display_name or student.username},\n\n"
            f"Congratulations — you finished “{course.title}” and earned "
            f"your certificate of completion.\n\n"
            f"Certificate number: {certificate.certificate_number}\n\n"
            "Well done,\nThe TeachFlow team"
        ),
        student.email,
    )


def notify_announcement(course, announcement):
    """Tell every enrolled student about a new announcement."""
    from apps.learning.models import Enrollment

    recipients = (
        Enrollment.objects.filter(course=course)
        .select_related("student")
        .values_list("student__email", flat=True)
    )
    for email in recipients:
        if not email:
            continue
        send_mail(
            f"New announcement on “{course.title}”: {announcement.title}",
            (
                f"Hi,\n\n"
                f"Your instructor posted a new announcement on “{course.title}”:\n\n"
                f"{announcement.title}\n{announcement.body}\n\n"
                "The TeachFlow team"
            ),
            FROM,
            [email],
            fail_silently=True,
        )
