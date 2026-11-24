"""Tests for coupons and discounts."""
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.payments.models import Coupon
from tests.helpers import make_course


def make_coupon(code="LEARN20", **kwargs):
    now = timezone.now()
    kwargs.setdefault("percent", 20)
    kwargs.setdefault("valid_from", now - timedelta(days=1))
    kwargs.setdefault("valid_until", now + timedelta(days=30))
    return Coupon.objects.create(code=code, **kwargs)


class CouponModelTests(TestCase):
    def test_discount_is_a_percentage_of_the_price(self):
        coupon = make_coupon(percent=25)
        self.assertEqual(coupon.discount_for(Decimal("100.00")), Decimal("25.00"))
        self.assertEqual(coupon.discount_for(Decimal("49.99")), Decimal("12.50"))

    def test_discount_never_exceeds_the_price(self):
        coupon = make_coupon(percent=90)
        self.assertEqual(coupon.discount_for(Decimal("10.00")), Decimal("9.00"))

    def test_site_wide_coupon_applies_to_any_course(self):
        coupon = make_coupon()
        self.assertTrue(coupon.applies_to(make_course()))
        self.assertTrue(coupon.applies_to(make_course(title="Other")))

    def test_one_course_coupon_only_applies_to_that_course(self):
        course = make_course()
        coupon = make_coupon(scope=Coupon.Scope.COURSE, course=course)
        self.assertTrue(coupon.applies_to(course))
        self.assertFalse(coupon.applies_to(make_course(title="Other")))

    def test_expired_coupon_does_not_apply(self):
        now = timezone.now()
        coupon = make_coupon(
            valid_from=now - timedelta(days=30),
            valid_until=now - timedelta(days=1),
        )
        self.assertFalse(coupon.is_valid_now())
        self.assertFalse(coupon.applies_to(make_course()))

    def test_coupon_that_has_not_started_does_not_apply(self):
        now = timezone.now()
        coupon = make_coupon(
            valid_from=now + timedelta(days=1),
            valid_until=now + timedelta(days=30),
        )
        self.assertFalse(coupon.is_valid_now())

    def test_inactive_coupon_does_not_apply(self):
        coupon = make_coupon(active=False)
        self.assertFalse(coupon.is_valid_now())

    def test_codes_are_unique(self):
        make_coupon(code="LEARN20")
        with self.assertRaises(Exception):
            make_coupon(code="LEARN20")

    def test_end_must_be_after_the_start(self):
        now = timezone.now()
        coupon = Coupon(
            code="BAD",
            percent=10,
            valid_from=now,
            valid_until=now - timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            coupon.full_clean()

    def test_one_course_coupon_needs_a_course(self):
        coupon = Coupon(
            code="NOCOURSE",
            percent=10,
            scope=Coupon.Scope.COURSE,
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            coupon.full_clean()

    def test_percent_is_capped_at_ninety(self):
        coupon = Coupon(
            code="TOOBIG",
            percent=95,
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            coupon.full_clean()
