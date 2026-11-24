"""Forms for the courses app."""
from django import forms

from .models import Course, Section


class CourseForm(forms.ModelForm):
    """Create or edit a course. The instructor and status are set by
    the view, never by the form — a student must not be able to make
    themselves the instructor, and a course starts as a draft."""

    class Meta:
        model = Course
        fields = (
            "title",
            "subtitle",
            "description",
            "price",
            "level",
            "language",
            "thumbnail_url",
            "category",
            "what_you_will_learn",
            "requirements",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "what_you_will_learn": forms.Textarea(attrs={"rows": 4}),
            "requirements": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price < 0:
            raise forms.ValidationError("A course price cannot be negative.")
        return price


class SectionForm(forms.ModelForm):
    """Add or rename a section of a course."""

    class Meta:
        model = Section
        fields = ("title", "order")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
