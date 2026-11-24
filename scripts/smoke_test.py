"""Release smoke test for TeachFlow.

Copies the project to a temporary folder (never touching the real
database or the working tree), then runs it the way a deployment
would: `check --deploy` and `collectstatic` with the production
settings, a live runserver on a test port, and a request against
each main page. Exits 0 when every check passes, 1 otherwise.

Usage:
    python scripts/smoke_test.py [--python PATH] [--port PORT]

The script makes its own 50+ character secret key for the run, so
no real secret is needed or written anywhere.
"""
import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url, timeout=10):
    """GET a URL without following redirects; return (status, body)."""
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(url, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


def wait_for_server(url, timeout=30):
    """Wait until the server answers anything at all."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            fetch(url)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--port", type=int, default=8124)
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parent.parent
    checks = []

    def check(name, passed, detail=""):
        checks.append((name, passed, detail))
        mark = "PASS" if passed else "FAIL"
        print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))

    work_dir = Path(tempfile.mkdtemp(prefix="teachflow-smoke-"))
    server = None
    try:
        shutil.copytree(
            project_dir,
            work_dir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                ".venv", ".git", "__pycache__", "*.pyc", "staticfiles",
                "db.sqlite3", "db.sqlite3-journal",
            ),
        )
        env = dict(os.environ)
        env["DJANGO_SETTINGS_MODULE"] = "config.settings.prod"
        env["DJANGO_SECRET_KEY"] = secrets.token_hex(32)
        env["DJANGO_ALLOWED_HOSTS"] = "127.0.0.1"
        env["DJANGO_EMAIL_BACKEND"] = (
            "django.core.mail.backends.console.EmailBackend"
        )
        env["DJANGO_SECURE_SSL_REDIRECT"] = "False"
        env.pop("DATABASE_URL", None)

        result = subprocess.run(
            [args.python, "manage.py", "check", "--deploy"],
            cwd=work_dir, env=env, capture_output=True, text=True, timeout=60,
        )
        output = result.stdout + result.stderr
        check(
            "deploy check passes with production settings",
            result.returncode == 0 and "security.W021" in output,
            output.strip().splitlines()[-1] if output.strip() else "",
        )

        result = subprocess.run(
            [args.python, "manage.py", "collectstatic", "--noinput"],
            cwd=work_dir, env=env, capture_output=True, text=True, timeout=120,
        )
        check(
            "collectstatic gathers the static files",
            result.returncode == 0,
            result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "",
        )

        # A deployment migrates a fresh database, so the smoke test
        # does the same instead of copying the developer's database.
        result = subprocess.run(
            [args.python, "manage.py", "migrate", "--noinput"],
            cwd=work_dir, env=env, capture_output=True, text=True, timeout=120,
        )
        check(
            "migrate builds a fresh database",
            result.returncode == 0,
            result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "",
        )

        server = subprocess.Popen(
            [args.python, "manage.py", "runserver", f"127.0.0.1:{args.port}",
             "--noreload"],
            cwd=work_dir, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        base = f"http://127.0.0.1:{args.port}"
        if not wait_for_server(base + "/health/"):
            check("runserver starts with production settings", False)
        else:
            check("runserver starts with production settings", True)
            status, body = fetch(base + "/")
            check("home page answers 200", status == 200 and "TeachFlow" in body)
            status, body = fetch(base + "/health/")
            check(
                "health endpoint answers with status ok",
                status == 200
                and json.loads(body) == {"status": "ok", "app": "teachflow"},
            )
            status, body = fetch(base + "/courses/")
            check(
                "course browse page answers 200",
                status == 200 and "Browse" in body,
            )
            status, _ = fetch(base + "/accounts/login/")
            check("login page answers 200", status == 200)
            status, _ = fetch(base + "/learning/dashboard/")
            check("student dashboard redirects anonymous users to login", status == 302)
            status, body = fetch(base + "/no-such-page/")
            check(
                "unknown page shows the custom 404 page",
                status == 404 and "Page not found" in body,
            )
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
        shutil.rmtree(work_dir, ignore_errors=True)

    failed = [name for name, passed, _ in checks if not passed]
    print()
    print(f"{len(checks) - len(failed)}/{len(checks)} smoke checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
