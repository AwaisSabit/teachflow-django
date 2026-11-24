"""Forms for the payments app: the simulated checkout."""
import re

from django import forms


class SimulatedCheckoutForm(forms.Form):
    """Card details for the simulated checkout.

    Nothing here is ever stored or sent anywhere: the numbers are
    checked for shape only (16 digits, a month/year, 3 digits), and
    the order is completed straight away. This is a demo checkout,
    not a payment gateway.
    """

    card_number = forms.CharField(
        max_length=19,
        help_text="Any 16-digit number — for example 4242 4242 4242 4242.",
    )
    expiry = forms.CharField(
        max_length=5, help_text="Month and year, as MM/YY."
    )
    cvc = forms.CharField(
        max_length=4, help_text="The 3-digit code on the back of the card."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_card_number(self):
        digits = re.sub(r"\D", "", self.cleaned_data["card_number"])
        if len(digits) != 16:
            raise forms.ValidationError("Enter a 16-digit card number.")
        return digits

    def clean_expiry(self):
        expiry = self.cleaned_data["expiry"].strip()
        if not re.fullmatch(r"(0[1-9]|1[0-2])\/\d{2}", expiry):
            raise forms.ValidationError("Enter the expiry as MM/YY.")
        return expiry

    def clean_cvc(self):
        cvc = self.cleaned_data["cvc"].strip()
        if not re.fullmatch(r"\d{3,4}", cvc):
            raise forms.ValidationError("Enter the 3-digit security code.")
        return cvc


class CouponForm(forms.Form):
    """Type a discount code at checkout."""

    code = forms.CharField(
        max_length=30, help_text="Enter your discount code, if you have one."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
