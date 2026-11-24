# TeachFlow

An online course platform in the style of Udemy: browse and buy courses, learn at your own pace with lessons and quizzes, earn certificates — or teach a course of your own.

Built as part of a 30-day portfolio challenge, Nov–Dec 2026.

## What it does

(Course list, enrolment, quizzes and certificates are being built — see `PROGRESS.md` for the build progress.)

## Stack

- Python 3.12, Django 5.1
- PostgreSQL in production (via `DATABASE_URL` or `POSTGRES_*` env vars); SQLite by default for local development
- Django templates + Bootstrap 5

## Install and run (local development)

```bash
cd teachflow-django
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # optional; dev works without it
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then open http://127.0.0.1:8000/ and http://127.0.0.1:8000/admin/.

## Useful checks

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

## Limitations

- No real payment gateway: paid enrolment uses a simulated checkout.
- No real video hosting: lesson videos are embedded from a URL the instructor provides.
