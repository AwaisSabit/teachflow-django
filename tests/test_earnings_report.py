"""Tests for the instructor earnings report."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.payments.models import Order, OrderItem
from tests.helpers import login_as, make_course, make_instructor, make_user
from tests.test_coupons import make_coupon


class EarningsReportTests(TestCase):
    def setUp(self):
        self.instructor = make_instructor()
        self.course = make_course(instructor=self.instructor, price=100)
        self.other = make_course(
            instructor=self.instructor, price=50, title="Flask in a Weekend"
        )
        login_as(self.client, self.instructor)

    def url(self):
        return reverse("payments:earnings_report")

    def buy(self, course, price, coupon=None, discount=0):
        buyer = make_user()
        order = Order.objects.create(
            student=buyer,
            total=price,
            coupon=coupon,
            discount_amount=discount,
        )
        OrderItem.objects.create(order=order, course=course, price=price)
        return order

    def test_report_shows_revenue_per_course(self):
        self.buy(self.course, Decimal("100"))
        self.buy(self.course, Decimal("100"))
        self.buy(self.other, Decimal("50"))
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python for Beginners")
        self.assertContains(response, "200")
        self.assertContains(response, "Flask in a Weekend")
        self.assertContains(response, "250")

    def test_coupon_discount_shows_as_the_gap_to_gross(self):
        coupon = make_coupon(code="LEARN20", percent=20)
        self.buy(
            self.course, Decimal("80"), coupon=coupon, discount=Decimal("20")
        )
        response = self.client.get(self.url())
        self.assertContains(response, "100")
        self.assertContains(response, "80")
        self.assertContains(response, "20")

    def test_csv_download_has_the_same_rows(self):
        import csv
        import io

        self.buy(self.course, Decimal("100"))
        response = self.client.get(self.url() + "?format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn(
            "teachflow-earnings.csv", response["Content-Disposition"]
        )
        rows = list(csv.reader(io.StringIO(response.content.decode())))
        self.assertEqual(
            rows[0],
            ["Course", "Units sold", "Gross", "Coupon discounts", "Revenue"],
        )
        course_row = [r for r in rows if r[0] == "Python for Beginners"][0]
        self.assertEqual(course_row[1], "1")
        self.assertEqual(Decimal(course_row[2]), Decimal("100.00"))
        self.assertEqual(Decimal(course_row[3]), Decimal("0.00"))
        self.assertEqual(Decimal(course_row[4]), Decimal("100.00"))
        total_row = [r for r in rows if r[0] == "Total"][0]
        self.assertEqual(total_row[1], "1")
        self.assertEqual(Decimal(total_row[4]), Decimal("100.00"))

    def test_other_instructors_courses_are_excluded(self):
        make_course(title="Someone Else's Course", price=999)
        response = self.client.get(self.url())
        self.assertNotContains(response, "Someone Else's Course")

    def test_student_gets_a_403(self):
        login_as(self.client, make_user(username="plain-student"))
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 403)

    def test_empty_state(self):
        login_as(self.client, make_instructor(username="new-teacher"))
        response = self.client.get(self.url())
        self.assertContains(response, "nothing to report")
