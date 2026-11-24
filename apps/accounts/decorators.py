"""Access helpers: who may teach."""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def instructor_required(view_func):
    """Only instructors may reach this view.

    Anonymous users are sent to the login page; a signed-in student
    gets a 403 — teaching is not something a student may do.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_instructor:
            raise PermissionDenied("Only instructors may do this.")
        return view_func(request, *args, **kwargs)

    return _wrapped
