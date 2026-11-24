# TeachFlow

**Version 1.0.0** — An online course platform in the style of Udemy: browse and buy courses, learn at your own pace with lessons and quizzes, earn certificates — or teach a course of your own.

Built as part of a 30-day portfolio challenge, Nov–Dec 2026.

## What it does

**For students**

- Browse published courses, search by text, filter by category, level and price (free or paid), sort and paginate the results.
- See course details: curriculum, instructor bio, what you will learn, requirements and a free preview lesson.
- Enrol for free on free courses, or buy paid courses through a simulated checkout (card details are checked for shape only and never stored).
- Wishlist courses, use the shopping cart, apply percentage discount codes (site-wide or for one course, with expiry dates), and see the full purchase history.
- Track progress lesson by lesson, with a progress bar and "continue where you left off" on the student dashboard.
- Take multiple-choice quizzes with auto-marking, a pass mark, unlimited retakes and a results page.
- Earn a certificate of completion (HTML page, numbered) once every lesson is finished and every quiz is passed.
- Ask the instructor questions on any lesson, and read course announcements.
- Get email notifications on enrolment, on earning a certificate and on new announcements (console backend in development).

**For instructors**

- Create, edit and delete courses, with a draft → submitted → published workflow and ownership checks throughout.
- Build sections and lessons (ordered, video URL embeds, text content, attachment lists, preview lessons).
- Create quizzes with multiple-choice questions, one correct answer each.
- Preview any course exactly as a student sees it, before publishing.
- Instructor dashboard: courses, students, enrolments, average ratings and earnings.
- Earnings report per course with coupon impact, downloadable as CSV.
- Post and delete course announcements; answer students' lesson questions.
- Admin panel with list displays, filters and search for courses, orders, enrolments, quizzes and certificates.

**Also included**

- Course recommendations ("students also bought", by category, most-enrolled first).
- Production security review (`manage.py check --deploy` clean except the deliberate HSTS-preload warning) and a release smoke test script (`python scripts/smoke_test.py`).
- Demo data seed command (`python manage.py seed_demo`) — demo instructor `demo-teacher`, demo student `demo-student`, password `DemoPass123!` (development only), three categories, four courses with sections, lessons and quizzes, enrolments, reviews and a 20% coupon code `LEARN20`.

## Stack

- Python 3.12, Django 5.1
- PostgreSQL in production (via `DATABASE_URL` or `POSTGRES_*` env vars); SQLite by default for local development
- Django templates + Bootstrap 5
- 301 tests, all passing (`python manage.py test`)

## Install and run (local development)

```bash
cd teachflow-django
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # optional; dev works without it
python manage.py migrate
python manage.py seed_demo   # optional demo data
python manage.py createsuperuser
python manage.py runserver
```

Then open http://127.0.0.1:8000/ and http://127.0.0.1:8000/admin/.

Demo logins after seeding: `demo-teacher` / `demo-student`, password `DemoPass123!` (development only — change before any real use).

## Useful checks

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
python scripts/smoke_test.py --python .venv/bin/python
```

## Limitations

- No real payment gateway: paid enrolment uses a simulated checkout.
- No real video hosting: lesson videos are embedded from a URL the instructor provides.
- Certificates are HTML pages, not PDFs.
- Email uses the console backend in development; set the SMTP settings in production.
