"""Production settings: DEBUG off, secret key mandatory, secure cookies."""
import os

from .base import *  # noqa: F401,F403

DEBUG = False

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY must be set in production")
if len(SECRET_KEY) < 50:
    raise ValueError(
        "DJANGO_SECRET_KEY must be at least 50 characters long in "
        "production — a short key leaves Django's signed data exposed"
    )

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if h.strip()
]
if not ALLOWED_HOSTS:
    raise ValueError("DJANGO_ALLOWED_HOSTS must be set in production")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# No JavaScript in this project reads the CSRF cookie (forms carry
# the token with {% csrf_token %}), so the cookie can be hidden from
# scripts as well.
CSRF_COOKIE_HTTPONLY = True
SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "True").lower() in {
    "1",
    "true",
    "yes",
}

# Strict Transport Security: once a browser has seen the header it
# only talks to this site over HTTPS for a year, including subdomains.
# Preload is left off — joining the preload list is hard to undo.
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False

# Refuse to guess a content type for responses, and do not send the
# full page address to other sites when following a link.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Email: password reset is a shipped feature, so production must be
# able to send mail. The default SMTP backend points at localhost:25,
# which is not a mail server — a reset on a live site would fail with
# a 500. Refuse to start with the SMTP backend unless a host is
# given, or set DJANGO_EMAIL_BACKEND to the console backend (for a
# test deployment) instead.
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("DJANGO_EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("DJANGO_EMAIL_USE_TLS", "True").lower() in {
    "1",
    "true",
    "yes",
}
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get(
    "DJANGO_DEFAULT_FROM_EMAIL", "noreply@localhost"
)
if EMAIL_BACKEND.endswith("smtp.EmailBackend") and not EMAIL_HOST:
    raise ValueError(
        "DJANGO_EMAIL_HOST must be set in production when using the SMTP "
        "email backend — password reset emails have nowhere to go without it"
    )

# Behind a reverse proxy (nginx, a load balancer), Django only sees
# plain HTTP unless the proxy is trusted to say the request arrived
# over HTTPS. Without this, SECURE_SSL_REDIRECT loops and HSTS never
# applies. Off by default: only turn it on when the proxy is yours
# and strips the header from outside traffic.
if os.environ.get("DJANGO_BEHIND_PROXY", "False").lower() in {
    "1",
    "true",
    "yes",
}:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
