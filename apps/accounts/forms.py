"""Forms for the accounts app: registration, login and profile."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class LoginForm(AuthenticationForm):
    """Sign-in form, with Bootstrap styling on its fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class RegistrationForm(UserCreationForm):
    """Create a new account: username, email, display name, role, password twice.

    The role is the user's answer to one question — do they want to
    learn, or to teach? Students learn; instructors can also create
    courses and see the instructor dashboard.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "display_name", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["role"].help_text = (
            "Choose “Student” to learn, or “Instructor” to teach courses too."
        )
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class ProfileForm(forms.ModelForm):
    """Update the signed-in user's display name, email and bio."""

    class Meta:
        model = User
        fields = ("display_name", "email", "bio")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
