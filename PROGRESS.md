# TeachFlow — build progress

A Udemy-level online course platform in Django. This file records what was built, in order. The README never carries day numbers.

## Release notes — TeachFlow 1.0.0

TeachFlow 1.0.0 is the first complete version of the platform: students can browse, buy and learn courses end to end, instructors can build and run them, and the whole flow is covered by 301 passing tests.

**Learning**

- Courses with categories, levels, prices, subtitles, learning outcomes and requirements; free preview lessons.
- Free enrolment and paid enrolment through a simulated checkout (no real payment gateway).
- Search, category/level/price filters, sorting and pagination on course lists.
- Lesson completion tracking with per-course progress, and a student dashboard with progress bars and "continue where you left off".
- Multiple-choice quizzes per lesson with auto-marking, a pass mark (70% by default), unlimited retakes and a results page.
- Certificate of completion (numbered HTML page) at 100% completion with every quiz passed.
- Lesson Q&A, course announcements, and "students also bought" recommendations by category.

**Buying**

- Wishlist, shopping cart with totals, percentage coupons (site-wide or per-course, with expiry), checkout with the coupon applied, and a purchase history page.
- Instructor earnings report per course with coupon impact and CSV export.

**Teaching**

- Instructor course create/edit/delete with a draft → submitted → published workflow and ownership checks.
- Instructor dashboard (courses, students, enrolments, average rating, earnings) and instructor preview mode to see a course as a student sees it.
- Admin customisation for courses, orders, enrolments, quizzes and certificates.

**Engineering**

- 301 tests, all passing, including security tests (`check --deploy` clean except the deliberate HSTS-preload warning), a release smoke test script, and a full end-to-end journey test.
- Demo data seed command (`python manage.py seed_demo`): demo instructor and student, three categories, four courses with sections, lessons and quizzes, enrolments and reviews.
- Email notifications (console backend in development) for enrolment, certificates and announcements.

**Known limitations**

- No real payment gateway and no real video hosting (lessons embed a URL the instructor provides).
- Certificates are HTML pages, not PDFs.
