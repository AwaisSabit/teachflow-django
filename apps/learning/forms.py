"""Forms for the learning app: quizzes and their questions."""
from django import forms

from .models import Quiz


class QuizForm(forms.ModelForm):
    """Create or edit a quiz for a lesson."""

    class Meta:
        model = Quiz
        fields = ("title", "pass_mark")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_pass_mark(self):
        mark = self.cleaned_data["pass_mark"]
        if mark < 1 or mark > 100:
            raise forms.ValidationError("The pass mark is between 1 and 100.")
        return mark


class QuizQuestionForm(forms.Form):
    """Add one multiple-choice question: the question, four answers,
    and which one is correct."""

    text = forms.CharField(
        label="Question", widget=forms.Textarea(attrs={"rows": 2})
    )
    choice_a = forms.CharField(label="Answer A", max_length=300)
    choice_b = forms.CharField(label="Answer B", max_length=300)
    choice_c = forms.CharField(label="Answer C", max_length=300)
    choice_d = forms.CharField(label="Answer D", max_length=300)
    correct = forms.ChoiceField(
        label="Correct answer",
        choices=[("a", "A"), ("b", "B"), ("c", "C"), ("d", "D")],
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["correct"].widget.attrs.pop("class", None)
