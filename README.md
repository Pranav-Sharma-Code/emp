# Examination Management Portal (EMP)

A role-based **Flask + SQLite** web application for managing oral / practical examinations.

- **Admin** creates courses and exams, defines a grading rubric and four date windows, assigns examiners and moves every exam through its lifecycle.
- **Examiner** (after Admin approval) publishes time slots and later scores every rubric criterion for each student.
- **Student** registers, searches exams, books one slot per exam, cancels before the deadline and finally sees marks and remarks.

Everything is server-rendered (Jinja2 + HTML forms). JavaScript is used only for the optional charts on the Admin *Reports* page.

---

## Table of contents

1. [Quick start](#1-quick-start)
2. [Features by role](#2-features-by-role)
3. [Technology stack](#3-technology-stack)
4. [Project structure (file by file)](#4-project-structure-file-by-file)
5. [Architecture and request flow](#5-architecture-and-request-flow)
6. [Database design](#6-database-design)
7. [Status lifecycles](#7-status-lifecycles)
8. [Business rules and where they are enforced](#8-business-rules-and-where-they-are-enforced)
9. [Services and helpers (function reference)](#9-services-and-helpers-function-reference)
10. [All routes](#10-all-routes)
11. [Templates and styling](#11-templates-and-styling)
12. [Security](#12-security)
13. [Scoring formula](#13-scoring-formula)
14. [Concurrency and transactions](#14-concurrency-and-transactions)
15. [Demo script (step by step)](#15-demo-script-step-by-step)
16. [Testing](#16-testing)
17. [Troubleshooting](#17-troubleshooting)
18. [Git, .gitignore and packaging](#18-git-gitignore-and-packaging)
19. [Known limitations and future work](#19-known-limitations-and-future-work)
20. [Viva questions and answers (100)](#20-viva-questions-and-answers-100)

---

## 1. Quick start

```bash
# 1. create and activate a virtual environment (Windows PowerShell)
python -m venv venv
venv\Scripts\activate

# 2. install the dependencies
pip install -r requirements.txt

# 3. run
python app.py
```

Open <http://127.0.0.1:5000>.

| What | Value |
|---|---|
| Admin e-mail | `admin@emp.com` |
| Admin password | `admin123` (change it before any real use) |
| Database file | `instance/app.db` (created automatically on first start) |
| Students | register themselves at `/register/student` (active at once) |
| Examiners | register at `/register/examiner` (status *pending* until the Admin approves) |

To reset everything: stop the server, delete `instance/app.db`, start again. `db.create_all()` only creates **missing** tables; it never alters existing ones, so delete the database after you change a model.

---

## 2. Features by role

### Admin
- Dashboard with totals (pending examiners, examiners, students, courses, exams) and a search box.
- **Examiners:** approval queue (approve / reject / deactivate / reactivate), profile with workload. Deactivation is refused while the examiner has upcoming slots with bookings.
- **Students:** list with search, profile with bookings, marks and activity log.
- **Courses:** create, edit, activate / deactivate, delete (blocked if the course has exams).
- **Exams:** create with four dates, edit and delete (Draft only), rubric criteria (weightage total ≤ 100), assign / remove examiners, lifecycle buttons, publish results.
- **Slots:** all slots with filters; slot page lists its students and lets the Admin **change the examiner**.
- **Bookings:** all bookings with filters, **reschedule** to another slot of the same exam, **cancel**, **CSV export**.
- **Search:** students, examiners, exams and bookings by name, e-mail, enrolment number or ID.
- **History:** completed exams with filters (course, date range) and marks.
- **Reports:** Chart.js charts (booking trend, examiner workload, booking status) and completion rate.

### Examiner
- Dashboard: assigned exams, slots created, students booked, pending evaluations.
- **My exams:** window dates, rubric, own slots.
- **Slots:** create (only in the creation window), edit and cancel (only before booking starts and only with no bookings), roster of students per slot.
- **Evaluations:** pending / done list; score form with one field per rubric criterion plus remarks.
- **Profile:** edit name, phone, department and password.
- An examiner who is not approved sees only a "pending" page.

### Student
- Dashboard: exams open for booking and upcoming bookings.
- **Exams:** search and filter by name, course, type and status; exam page with slots and seats left.
- **Book** a slot, **cancel** before the booking deadline, **My bookings**, **History** (all bookings and activity log).
- **Results:** published marks, per-criterion breakdown and examiner remarks.
- **Profile:** edit name, phone and password.

---

## 3. Technology stack

| Technology | Version | Why it is used |
|---|---|---|
| Python | 3.14 | Language of the back-end |
| Flask | 3.1.3 | Web framework: routes, blueprints, sessions, flash messages, templates |
| Flask-SQLAlchemy | 3.1.1 | Connects SQLAlchemy to Flask (`db`, `db.Model`, `db.session`) |
| SQLAlchemy | 2.1.4 | ORM: models, constraints, queries, transactions |
| SQLite | 3 (built into Python) | One-file database, no server to install |
| Werkzeug | 3.1.9 | `generate_password_hash`, `check_password_hash`; signs the session cookie |
| Jinja2 | 3.1.6 | Template engine: inheritance (`base.html`), loops, auto-escaping |
| itsdangerous, click, blinker, MarkupSafe | 2.2.0 / 8.5.0 / 1.9.0 / 3.0.4 | Installed automatically as Flask dependencies |
| HTML5 + CSS3 | – | 38 templates and one stylesheet, `static/style.css` (no CSS framework) |
| Chart.js | 4.4.1 (CDN) | Optional charts on `/admin/reports` only |

`requirements.txt` lists only `Flask`, `Flask-SQLAlchemy` and `SQLAlchemy`; everything else is installed as a dependency.

---

## 4. Project structure (file by file)

```
emp/
├── app.py                 Creates the Flask app, config, registers blueprints, db.create_all(), seeds the Admin
├── extensions.py          db = SQLAlchemy()  (kept separate to avoid circular imports)
├── helpers.py             role_req, examiner_required, slot_creation_open, slots_editable, booking_open
├── requirements.txt       Flask, Flask-SQLAlchemy, SQLAlchemy (pinned)
├── .gitignore             venv, __pycache__, instance/, *.db, *.bak, .env, editor files, *.zip
├── README.md              this file
│
├── models/                one file per table
│   ├── __init__.py        imports every model so create_all() knows all tables
│   ├── enums.py           Python enums + sa_enum() (stores lowercase values in the DB)
│   ├── mixins.py          TimestampMixin (created_at column)
│   ├── user.py            users
│   ├── course.py          courses
│   ├── exam.py            exams
│   ├── exam_examiner.py   exam_examiners (which examiner is assigned to which exam)
│   ├── rubric.py          rubrics (grading criteria)
│   ├── slot.py            slots
│   ├── booking.py         bookings (+ partial unique index)
│   ├── booking_history.py booking_history (audit trail)
│   └── evaluation.py      evaluations and evaluation_scores
│
├── routes/                thin route handlers (read form -> call service -> render / redirect)
│   ├── auth.py            /login, /register/<role>, /logout
│   ├── admin.py           dashboard, examiners, courses
│   ├── admin_exam.py      exams, rubrics, examiner assignment, lifecycle buttons
│   ├── admin_extra.py     students, slots, bookings, search, history, reports, CSV
│   ├── examiner.py        dashboard, exams, slots, roster, evaluations, profile
│   └── student.py         dashboard, exams, booking, history, results, profile
│
├── services/              business rules (one transaction per action)
│   ├── booking_service.py     book(), cancel()  + _clashes(), _log()
│   ├── evaluation_service.py  submit(), calculate_total()
│   ├── admin_service.py       reschedule(), cancel_booking(), change_examiner()
│   └── profile_service.py     update_profile()
│
├── templates/             38 Jinja2 files
│   ├── base.html          layout, role-aware navbar, flash messages
│   ├── home.html, pending.html, profile.html
│   ├── auth/              login.html, register.html
│   ├── admin/             17 pages (dashboard, courses, exams, slots, bookings, reports ...)
│   ├── examiner/          8 pages (dashboard, exams, slots, evaluate ...)
│   └── student/           7 pages (dashboard, exams, bookings, results ...)
│
├── static/style.css       the only stylesheet (~220 lines)
├── instance/app.db        SQLite database (git-ignored, created at first run)
└── report/                project report (report.html -> EMP_Report.pdf)
```

`admin.py`, `admin_exam.py` and `admin_extra.py` all belong to the **same** `admin` blueprint (`/admin` prefix); the last two import `admin_bp` from `admin.py`. They are imported in `app.py` **before** `register_blueprint`, because Flask does not allow adding routes to a blueprint after it is registered.

---

## 5. Architecture and request flow

```
Browser (Jinja2 pages + plain HTML forms)
   |  request
   v
Flask blueprint route   -> decides WHO may call it (role_req / examiner_required)
   |  reads form / URL
   v
Service layer           -> decides WHETHER the action is allowed (rules, guards, transaction)
   |
   v
SQLAlchemy models       -> store the result (constraints are a second line of defence)
   |
   v
SQLite  instance/app.db
```

Example: **student books a slot**

1. `POST /student/slots/<id>/book` -> `student.book` (role must be `student`, else 403).
2. The route calls `booking_service.book(student_id, slot_id)`.
3. The service checks: exam is Booking Open and now is inside the window; slot not cancelled; no active booking for this exam; no time clash; then runs the guarded `UPDATE`.
4. It inserts the booking and a history row, updates the slot status, commits.
5. The route flashes the message and redirects (Post-Redirect-Get).

---

## 6. Database design

Ten tables in one SQLite file. Admin, Examiner and Student share the single `users` table, told apart by `role`. Every table has an auto-increment `id` primary key and a `created_at` column.

### users
| Column | Type | Notes |
|---|---|---|
| id | Integer | primary key |
| name | String(100) | required |
| email | String(120) | **unique**, required, used to log in (stored lower-case) |
| password | String(255) | Werkzeug hash, never the real password |
| role | enum | `admin`, `student`, `examiner` (default student) |
| status | enum | `active`, `pending`, `rejected`, `inactive` (default pending) |
| phone | String(20) | optional |
| department | String(100) | examiners only |
| enrollment_no | String(30) | **unique**, students only |

### courses
`id`, `code` (String(10), **unique**), `name`, `description`, `status` (Boolean, `True` = active).

### exams
| Column | Notes |
|---|---|
| course_id | FK -> courses |
| name | |
| exam_type | `viva`, `practical`, `project`, `assessment` |
| duration_minutes | integer, > 0 |
| max_marks | integer, > 0 |
| status | `draft`, `slotcreation`, `bookingopen`, `closed`, `completed` (default draft) |
| slot_create_start, slot_create_end | when examiners may create slots (DateTime) |
| booking_start, booking_end | when students may book (DateTime) |
| results_published | Boolean, default false |

CHECK constraints: `duration_minutes > 0`, `max_marks > 0`, `slot_create_end >= slot_create_start`, `booking_end > booking_start`.

### exam_examiners
`id`, `exam_id` FK, `examiner_id` FK -> users, `assigned_by` FK -> users (nullable). **Unique** `(exam_id, examiner_id)`. This is the many-to-many link between exams and examiners.

### rubrics
`id`, `exam_id` FK, `criterion_name`, `max_marks` (> 0), `weightage` (Numeric(5,2), 0 < w <= 100), `description`. The weightages of one exam must total 100 before the exam can leave Draft.

### slots
| Column | Notes |
|---|---|
| exam_id | FK -> exams |
| examiner_id | FK -> users (the Admin can change it) |
| slot_date, start_time, end_time | Date, Time, Time |
| capacity | maximum students, > 0 |
| available_seats | starts equal to capacity, drops by 1 per booking |
| status | `available`, `full`, `cancelled`, `completed` |

CHECK constraints: `capacity > 0`, `available_seats >= 0 AND available_seats <= capacity`, `end_time > start_time`.

### bookings
`id`, `student_id` FK, `slot_id` FK, `exam_id` FK, `booking_date`, `status` (`booked`, `cancelled`, `completed`), `old_slot_id` FK (filled when the Admin reschedules).
**Partial unique index** `unique_active_booking` on `(student_id, exam_id) WHERE status = 'booked'` -> a student can have only one *active* booking per exam, but may book again after cancelling. Bookings are never deleted; a cancelled booking keeps its row.

### booking_history
`id`, `booking_id` FK, `action` (`book`, `cancel`, `reschedule`, `examiner_change`, `completed`), `from_slot_id`, `to_slot_id`, `acted_by` FK -> users, `note`. Audit trail; rows are never deleted.

### evaluations
`id`, `booking_id` FK (**unique**: one evaluation per booking), `examiner_id` FK, `status` (`draft`, `submitted`), `total_marks` (Numeric(6,2)), `remarks`.

### evaluation_scores
`id`, `evaluation_id` FK, `rubric_id` FK, `marks` (Numeric(6,2), >= 0). **Unique** `(evaluation_id, rubric_id)`: one score per criterion.

### Relationships
- one course -> many exams
- one exam -> many rubrics, slots, bookings, assigned examiners
- one user (examiner) -> many slots; one user (student) -> many bookings
- one slot -> many bookings
- one booking -> many history rows, at most one evaluation
- one evaluation -> many evaluation_scores (one per rubric criterion)

---

## 7. Status lifecycles

| Entity | Moves |
|---|---|
| **Exam** | `draft` -> `slotcreation` (needs weightage = 100 and >= 1 examiner) -> `bookingopen` -> `closed` -> `completed` (needs every booking evaluated); then *publish results* |
| **Slot** | `available` <-> `full` as seats change; `cancelled` if the examiner removes it; `completed` when the exam is completed |
| **Booking** | `booked` -> `cancelled` (student or Admin) **or** `booked` -> `completed` (after the evaluation is submitted) |
| **Evaluation** | `draft` -> `submitted` |
| **Examiner** | `pending` -> `active` or `rejected`; `active` <-> `inactive` |
| **Student** | `active` from registration |

Each exam step is an Admin button, **and** the date windows must also hold, so a stale "open" status cannot bypass a deadline.

Date order for an exam: `slot_create_start <= slot_create_end <= booking_start < booking_end`.

---

## 8. Business rules and where they are enforced

| Rule | Enforced in |
|---|---|
| Examiners create slots only in the creation period | `helpers.slot_creation_open` (status Slot Creation **and** now inside the window) + examiner must be assigned to the exam |
| Edit / cancel slots only before booking starts, and only if nobody booked | `helpers.slots_editable` + `booked_count == 0` in `routes/examiner.py` |
| No two slots of one examiner overlap | `has_clash` in `routes/examiner.py` |
| Students book only in the booking period | `helpers.booking_open` used in `booking_service.book` |
| **No overbooking** | `UPDATE slots SET available_seats = available_seats - 1 WHERE id=? AND available_seats > 0`; 0 rows changed means full. Plus `CHECK(available_seats >= 0 ...)` |
| Slot becomes Full at 0 seats; reopens on cancel / reschedule | `booking_service` and `admin_service` |
| One active booking per exam | service pre-check + partial unique index (second line of defence, `IntegrityError` is caught) |
| No overlapping bookings for a student | `booking_service._clashes` (same date, overlapping times) |
| Cancel only before the booking deadline | `booking_service.cancel` (status Booked and now < `booking_end`), seat returned |
| Examiner evaluates only own students | `my_slot_or_403` in `routes/examiner.py` + check in `evaluation_service.submit` |
| Evaluation only when the exam is Closed and results are not published | `evaluation_service.submit` |
| Marks within 0..criterion max, all criteria required | `evaluation_service.submit` |
| Results visible only when evaluation is submitted **and** results published | `student.result_detail` (404 otherwise), `student.results` query |
| Exam cannot leave Draft unless weightage = 100 and an examiner is assigned | `exam_status` in `routes/admin_exam.py` |
| Exam cannot be completed while bookings are still unevaluated | `exam_status` (counts bookings with status `booked`) |
| Exam / rubric changes only in Draft | `exam_edit`, `exam_delete`, `rubric_new`, `rubric_delete` |
| Course cannot be deleted if it has exams | `course_delete` |
| Examiner cannot be deactivated with upcoming booked slots | `examiner_action` in `routes/admin.py` |
| Reschedule: same exam, free seat, no clash, one transaction, logged | `admin_service.reschedule` |
| Change examiner: approved examiner, no time clash, logged for each booking | `admin_service.change_examiner` |
| Full history for every booking | `booking_history` rows written by every service |
| Examiners need approval | `helpers.examiner_required` shows `pending.html` unless status is `active` |

---

## 9. Services and helpers (function reference)

### `helpers.py`
| Function | Purpose |
|---|---|
| `role_req(role)` | Decorator. Not logged in -> redirect to login. Wrong role -> `abort(403)`. |
| `examiner_required` | Decorator. Logged in as examiner **and** status `active`, otherwise the "pending" page. |
| `slot_creation_open(exam)` | True if status is Slot Creation and `slot_create_start <= now <= slot_create_end`. |
| `slots_editable(exam)` | True if status is Slot Creation and now < `booking_start`. |
| `booking_open(exam)` | True if status is Booking Open and `booking_start <= now <= booking_end`. |

### `services/booking_service.py`
| Function | Purpose |
|---|---|
| `book(student_id, slot_id)` | All booking guards, guarded seat update, creates the booking and a history row. Returns `(ok, message)`. |
| `cancel(student_id, booking_id)` | Own active booking, before the deadline; returns the seat; Full -> Available; history row. |
| `_clashes(student_id, slot, ignore_booking_id=None)` | Does the student already have an overlapping booked slot? |
| `_log(...)` | Writes one `booking_history` row. |

### `services/evaluation_service.py`
| Function | Purpose |
|---|---|
| `calculate_total(rubrics, marks, exam_max)` | The scoring formula using `Decimal` (see section 13). |
| `submit(examiner_id, booking_id, raw_marks, remarks)` | Validates, creates / updates the evaluation and its scores, sets total, marks the booking Completed, writes history. |

### `services/admin_service.py`
| Function | Purpose |
|---|---|
| `reschedule(booking_id, new_slot_id, admin_id)` | Moves a booking to another slot of the same exam; seats and statuses updated in one transaction; logged. |
| `cancel_booking(booking_id, admin_id)` | Admin cancel (no deadline), returns the seat, logged. |
| `change_examiner(slot_id, examiner_id, admin_id)` | Gives the slot to another approved examiner without a time clash; logs `examiner_change` for each booking. |

### `services/profile_service.py`
| Function | Purpose |
|---|---|
| `update_profile(user, form)` | Validates name / phone / department and the optional password change; nothing is changed unless every check passes. |

---

## 10. All routes

57 routes. Every page after login lives under its role prefix; opening another role's URL gives **403**. POST routes are plain HTML form submissions followed by a redirect.

### Public and authentication
| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Landing page |
| GET, POST | `/login` | Login for all roles, redirects by role |
| GET, POST | `/register/<role>` | `student` or `examiner` registration (examiner starts pending) |
| POST | `/logout` | End the session |

### Admin (`/admin`)
| Method | Route | Purpose |
|---|---|---|
| GET | `/admin/dashboard` | Totals, pending examiners, search box |
| GET | `/admin/examiners` | Examiner list / approval queue |
| GET | `/admin/examiners/<id>` | Examiner profile and workload |
| POST | `/admin/examiners/<id>/<action>` | `approve`, `reject`, `deactivate`, `reactivate` |
| GET | `/admin/students` | Student list with search (`?q=`) |
| GET | `/admin/students/<id>` | Student profile, bookings, activity log |
| GET | `/admin/courses` | Course list |
| GET, POST | `/admin/courses/new` | Create course |
| GET, POST | `/admin/courses/<id>/edit` | Edit course |
| POST | `/admin/courses/<id>/toggle` | Activate / deactivate |
| POST | `/admin/courses/<id>/delete` | Delete (blocked if it has exams) |
| GET | `/admin/exams` | Exam list |
| GET, POST | `/admin/exams/new` | Create exam with four dates |
| GET | `/admin/exams/<id>` | Exam page: rubric, examiners, status buttons |
| GET, POST | `/admin/exams/<id>/edit` | Edit (Draft only) |
| POST | `/admin/exams/<id>/delete` | Delete (Draft only) |
| POST | `/admin/exams/<id>/status/<action>` | `open-slot-creation`, `open-booking`, `close-booking`, `complete`, `publish-results` |
| POST | `/admin/exams/<id>/rubrics/new` | Add rubric criterion |
| POST | `/admin/exams/<id>/rubrics/<rid>/delete` | Remove criterion |
| POST | `/admin/exams/<id>/examiners/add` | Assign an examiner |
| POST | `/admin/exams/<id>/examiners/<uid>/remove` | Remove an assigned examiner |
| GET | `/admin/slots` | All slots (`?exam=&examiner=&status=`) |
| GET | `/admin/slots/<id>` | Slot detail and its students |
| POST | `/admin/slots/<id>/change-examiner` | Change the examiner |
| GET | `/admin/bookings` | All bookings (`?exam=&status=`) |
| GET | `/admin/bookings/<id>` | Booking detail, reschedule form, history |
| POST | `/admin/bookings/<id>/reschedule` | Move to another slot of the same exam |
| POST | `/admin/bookings/<id>/cancel` | Admin cancels a booking |
| GET | `/admin/bookings/export.csv` | Bookings as CSV (honours the filters) |
| GET | `/admin/search` | `?q=&type=` students, examiners, exams, bookings |
| GET | `/admin/history` | Completed exams (`?course=&from=&to=`) |
| GET | `/admin/reports` | Charts and completion rate |

### Examiner (`/examiner`)
| Method | Route | Purpose |
|---|---|---|
| GET | `/examiner/dashboard` | Assigned exams, slots, booked students, pending evaluations |
| GET | `/examiner/exams` | Assigned exams |
| GET | `/examiner/exams/<id>` | Exam, rubric and own slots |
| GET | `/examiner/slots` | My slots |
| GET, POST | `/examiner/slots/new?exam=<id>` | Create a slot (creation window only) |
| GET, POST | `/examiner/slots/<id>/edit` | Edit a slot |
| POST | `/examiner/slots/<id>/cancel` | Cancel a slot (soft delete) |
| GET | `/examiner/slots/<id>/students` | Roster of one slot |
| GET | `/examiner/evaluations` | Pending and finished evaluations |
| GET, POST | `/examiner/evaluate/<booking_id>` | Score every criterion + remarks |
| GET, POST | `/examiner/profile` | Edit contact details and password |

### Student (`/student`)
| Method | Route | Purpose |
|---|---|---|
| GET | `/student/dashboard` | Open exams and upcoming bookings |
| GET | `/student/exams` | Search / filter (`?q=&course=&type=&status=`) |
| GET | `/student/exams/<id>` | Exam with slots and seats left |
| POST | `/student/slots/<id>/book` | Book a slot |
| GET | `/student/bookings` | My active bookings |
| POST | `/student/bookings/<id>/cancel` | Cancel before the deadline |
| GET | `/student/history` | All bookings and activity log |
| GET | `/student/results` | Published results |
| GET | `/student/results/<booking_id>` | Marks per criterion and remarks |
| GET, POST | `/student/profile` | Edit profile and password |

---

## 11. Templates and styling

- `base.html` is the shared layout: navbar (links depend on `session.role`), flash messages (`get_flashed_messages()`), and `{% block content %}`. Every page extends it.
- Folders match the role prefixes: `templates/admin/`, `templates/examiner/`, `templates/student/`, `templates/auth/`. The path in `render_template("admin/exams.html")` is counted from the `templates` folder and is case-sensitive.
- Forms that change data are always `<form method="post">`; links are used only for navigation.
- `static/style.css` has small reusable classes: `.btn` (`.light`, `.small`, `.danger`), `.badge` (coloured status pills), `.alert`, `.box` (narrow form), `.filters`, `.actions`, `.back`, `.chart`.
- The only JavaScript is on `admin/reports.html` (Chart.js from a CDN). Without JavaScript every other feature works.

---

## 12. Security

- Passwords are stored only as Werkzeug hashes (salted); login uses `check_password_hash`.
- The login error is the same for a wrong e-mail and a wrong password ("Wrong email or password").
- Flask's signed-cookie session stores `user_id`, `role`, `name`. It is signed with `SECRET_KEY`, so it cannot be edited by the user.
- Access control: `role_req` (role) and `examiner_required` (role + approval). Object-level checks live in the routes/services: an examiner can open only their own slots and students (403), a student can open only their own bookings and results (404).
- The role is never taken from a form; registration sets it from the URL (`student` or `examiner`) and only those two values are accepted.
- All database access goes through SQLAlchemy (parameterised queries); Jinja2 auto-escaping is on, which prevents stored XSS.
- State-changing actions are POST forms (approve, delete, cancel, book, logout, ...), never plain links.
- **Not implemented yet:** CSRF tokens (Flask-WTF). `SECRET_KEY` and the default Admin password in `app.py` are development values.

---

## 13. Scoring formula

For each rubric criterion: `awarded / criterion_max x weightage`.
Add them up, divide by 100, multiply by the exam's `max_marks`.

```
total = ( SUM( awarded_i / max_i * weightage_i ) / 100 ) * exam_max_marks
```

**Worked example.** Exam max marks = 36. Criteria: A (max 40, weightage 50) and B (max 56, weightage 50). The student gets 40 and 28.

```
A: 40 / 40 * 50 = 50
B: 28 / 56 * 50 = 25
sum = 75   ->   75 / 100 * 36 = 27.00
```

`Decimal` is used (not float) so marks are exact; the result is rounded to 2 decimals. Rubric weightages must total 100 before the exam can leave Draft.

---

## 14. Concurrency and transactions

SQLite allows one writer at a time. A booking runs in one transaction:

1. `UPDATE slots SET available_seats = available_seats - 1 WHERE id = ? AND available_seats > 0`.
2. If **0 rows** changed, the slot was already full -> `rollback`, message "Sorry, this slot is full".
3. Otherwise insert the booking, `flush()` (to get its id), write the history row, set the slot to Full when seats reach 0, and `commit()`.
4. A database `IntegrityError` (duplicate active booking) is caught and rolled back.

Because the "is a seat free?" check and the decrement are one SQL statement decided by the database, two simultaneous requests can never both take the last seat. Cancel and reschedule use the same style of update (`+ 1`).

---

## 15. Demo script (step by step)

1. Start the app, log in as **admin@emp.com / admin123**.
2. Register a **student** and an **examiner** (log out between registrations). The examiner sees the *pending* page.
3. Admin -> **Examiners** -> **Approve**.
4. Admin -> **Courses** -> create `CS101`.
5. Admin -> **Exams** -> new exam. Dates must satisfy `slot_create_start <= slot_create_end <= booking_start < booking_end`, and the slot-creation window must contain *now* while the examiner creates slots.
6. On the exam page: add rubric criteria (total weightage 100), assign the examiner, click **Open slot creation**.
7. Examiner -> exam -> **+ New Slot** (try an overlapping slot to see the refusal).
8. Admin -> **Close slot creation and open booking** (the booking window must contain *now*).
9. Student -> **Exams** -> book a slot. Try booking a second slot (refused), cancel and re-book. With a second student, fill a slot to show "full".
10. Admin -> **Close booking**. Examiner -> **Evaluations** -> **Evaluate** (marks above the maximum are refused).
11. Admin -> **Mark as completed** (refused while any booking is unevaluated) -> **Publish results**.
12. Student -> **Results** (hidden before publishing).
13. Admin extras: reschedule a booking, change a slot's examiner, search, history, reports, CSV export.

---

## 16. Testing

- Manual walkthrough of the demo script above.
- During development the whole system was exercised with scripted request-level checks using Flask's test client (79 assertions, all passing): every page for every role; booking and seat counts; duplicate, full and clash refusals; cancel returns the seat; evaluation maths and range checks; 403 / 404 access rules; reschedule; change examiner; deactivation rule; profile and password changes.
- Clean-install check: in a brand-new virtual environment `pip install -r requirements.txt` then `python app.py` creates the database and the Admin and serves every page.

---

## 17. Troubleshooting

| Error / symptom | Cause and fix |
|---|---|
| `jinja2.exceptions.TemplateNotFound: admin/exams.html` | File name or folder does not match the `render_template` path (for example `exam.html` instead of `exams.html`, or the folder inside `auth/`). Names are case-sensitive. |
| `ModuleNotFoundError: No module named 'services'` | The `services/` folder must be in the project root next to `app.py` (not inside `templates/`) and contain `__init__.py`. |
| `ImportError: cannot import name 'render_templatem'` | Typo in an import. Read the **last** line of the traceback. |
| `TypeError: unsupported operand type(s) for +: 'UserRole' and 'str'` | An enum column returns an enum object; use `.value` (for example `user.role.value`). |
| `The setup method 'route' can no longer be called on the blueprint` | A route file was imported **after** `register_blueprint`. Import `routes.admin_exam` and `routes.admin_extra` before registering. |
| New column / table does not appear | `db.create_all()` does not alter existing tables. Stop the server, delete `instance/app.db`, start again. |
| "Booking is not open for this exam right now" | Status **and** dates must both allow it. Check the exam's booking window against the current time. |
| Cannot delete `instance/app.db` on Windows | Stop the Flask server first (Ctrl+C); the file is locked while it runs. |
| Page looks unstyled | Hard refresh (Ctrl+F5); check `static/style.css` is linked in `base.html`. |

---

## 18. Git, .gitignore and packaging

- `.gitignore` excludes: `venv/` and other environments, `__pycache__/` and `*.py[cod]`, `instance/`, `*.db`, `*.sqlite3`, `*.bak`, `.env*`, editor / OS files, `*.zip`, build folders. The database is created automatically, so it is never committed.
- **To submit:** make one ZIP with a single root folder (for example `emp/`) containing the source, `requirements.txt`, `README.md` and `report/`. Leave out `venv/`, `instance/`, `.git/` and `__pycache__/`.
- After unzipping, the grader runs `pip install -r requirements.txt` and `python app.py`.

---

## 19. Known limitations and future work

- CSRF protection (Flask-WTF tokens) is not implemented; `SECRET_KEY` and the default Admin password are development values.
- The optional JSON API (`/api/v1`), PDF scorecard and e-mail notifications are not implemented. Lists are not paginated.
- A booked student who does not attend must still be evaluated (for example with 0) or cancelled by the Admin before the exam can be completed; there is no separate "absent" status.
- Removing an assigned examiner from an exam is hidden in the UI after Slot Creation, but the route itself does not check the status.
- Times are stored as local time without a time zone; SQLite allows one writer at a time.
- Schema changes need a manual database reset (no migrations tool such as Flask-Migrate).

---

## 20. Viva questions and answers (100)

### A. Project and requirements

**Q1. What is EMP and what problem does it solve?**
A. It is a web portal to run oral / practical exams: the Admin schedules exams, examiners publish slots and grade, students book slots and see results. It replaces manual lists and spreadsheets and enforces the rules (windows, capacity, one booking per exam) automatically.

**Q2. Which roles exist and what can each do?**
A. Admin (superuser: courses, exams, rubrics, approvals, overrides, reports), Examiner (slots, roster, evaluation, only after approval) and Student (search, book, cancel, results).

**Q3. Why Flask and SQLite?**
A. The brief asks for a Flask back-end and SQLite. Flask is small and easy to explain; SQLite needs no server, is created in code and runs on any laptop for the demo.

**Q4. Why is the app server-rendered with no JavaScript in the core?**
A. Every action is an HTML form post or link, so the core works in any browser and is easy to test and secure. JavaScript is only used for the optional charts.

**Q5. How is the Admin created?**
A. On first start `app.py` runs `db.create_all()` and, if no user with role `admin` exists, inserts one (`admin@emp.com`, password stored hashed).

**Q6. Why is there no Admin registration page?**
A. Anyone could otherwise make themselves an Admin. The Admin must pre-exist, so it is seeded in code.

**Q7. Why do examiners need approval and how is it enforced?**
A. The Admin must trust who can grade. A new examiner has status `pending`; `examiner_required` shows the "pending" page for every examiner route until the status is `active`.

**Q8. Why did you use plain CSS instead of Bootstrap?**
A. The brief allows Bootstrap but does not require it. One small hand-written stylesheet keeps the project simple, has no external dependency and is easy to explain.

**Q9. How do you run the project from scratch?**
A. Create a virtual environment, `pip install -r requirements.txt`, `python app.py`, open `http://127.0.0.1:5000`, log in as `admin@emp.com` / `admin123`.

**Q10. What are the main limitations?**
A. No CSRF tokens yet, no JSON API / PDF scorecard / e-mail, no pagination, no migrations, development secret key and default password (see section 19).

### B. Flask and web basics

**Q11. Explain the request flow in your application.**
A. Browser -> blueprint route (role check) -> service (rules) -> SQLAlchemy model -> SQLite, then the route renders a Jinja2 template or redirects.

**Q12. What is a blueprint and which ones do you have?**
A. A blueprint groups related routes. I have `auth`, `admin`, `examiner` and `student` (the admin blueprint is split over three files for readability).

**Q13. Why are `routes.admin_exam` and `routes.admin_extra` imported before `register_blueprint(admin_bp)`?**
A. They add routes to `admin_bp` using decorators. Flask forbids adding routes to a blueprint after it has been registered.

**Q14. What is an application context and why `with app.app_context(): db.create_all()`?**
A. It tells Flask-SQLAlchemy which app the database belongs to. Outside a request there is no context, so it is created manually to run `create_all()` and seed the Admin at startup.

**Q15. What does `db.init_app(app)` do and why is `db` in `extensions.py`?**
A. It connects the shared `db` object to the app. Keeping `db` in its own file lets models and routes import it without circular imports.

**Q16. What is a decorator? Explain `role_req`.**
A. A function that wraps another function. `role_req("admin")` checks the session before the view runs: not logged in -> redirect to login; wrong role -> 403; otherwise the view runs.

**Q17. When do you return 403, 404 and 302?**
A. 403: logged in but wrong role or someone else's slot/student (examiner). 404: item does not exist or must be hidden (another student's result). 302: redirect after a POST or when login is needed.

**Q18. What is a Flask session and what does it store here?**
A. Data kept between requests in a signed cookie. I store `user_id`, `role` and `name`. It is signed with `SECRET_KEY`, so the browser cannot change it without detection.

**Q19. Why are logout, delete, approve and book POST requests and not links?**
A. GET must be safe: browsers, crawlers and prefetchers open links. A POST form means the action only happens when the user submits it deliberately.

**Q20. What is the Post-Redirect-Get pattern?**
A. After a POST the server redirects to a GET page. Refreshing the page then does not resubmit the form (no double booking or double create).

**Q21. What is `url_for` and why use it?**
A. It builds a URL from the endpoint name (for example `url_for('admin.exams')`). If a route path changes, no link breaks.

**Q22. What is `flash`?**
A. It stores a one-time message in the session; `get_flashed_messages()` in `base.html` shows it on the next page.

**Q23. What is Jinja2 template inheritance?**
A. `base.html` defines the layout and a `{% block content %}`; each page `{% extends "base.html" %}` and fills the block, so the navbar and flash messages are written once.

**Q24. What is auto-escaping and why does it matter?**
A. Jinja2 converts `<`, `>`, `&` and quotes in variables to HTML entities, so user text cannot inject a `<script>` (stored XSS).

**Q25. What is the difference between `request.form` and `request.args`?**
A. `request.form` holds POST body fields; `request.args` holds the URL query string (`?q=math`). Filters use `args`, forms use `form`.

**Q26. What does `Flask(__name__)` do?**
A. It creates the app and tells Flask where to find templates and static files relative to the module.

**Q27. Why a service layer?**
A. Business rules live in one place, so a route, a test or a future API all enforce the same rule. Routes stay short and readable.

**Q28. What are the risks of `debug=True`?**
A. The interactive debugger can run code if exposed. It is fine on a local demo but must be off in production.

### C. Database and SQLAlchemy

**Q29. List the tables.**
A. `users`, `courses`, `exams`, `exam_examiners`, `rubrics`, `slots`, `bookings`, `booking_history`, `evaluations`, `evaluation_scores`.

**Q30. Why one `users` table for all roles?**
A. All roles share name, e-mail, password and status, so one table with a `role` column is simpler than three tables. Role-specific fields (`department`, `enrollment_no`) are just empty for other roles.

**Q31. What are a primary key and a foreign key? Give an example.**
A. A primary key uniquely identifies a row (`exams.id`); a foreign key points to another table's primary key (`exams.course_id` -> `courses.id`).

**Q32. What is an ORM?**
A. It maps Python classes to tables and objects to rows, so I write `Exam.query.get(1)` instead of SQL. SQLAlchemy is the ORM used.

**Q33. What do `nullable`, `unique` and `default` mean in `db.Column`?**
A. `nullable=False` -> required; `unique=True` -> no duplicates (e-mail, course code); `default=` -> value used when none is given (for example exam status `draft`).

**Q34. What does `db.create_all()` do and what can it not do?**
A. It creates tables that do not exist. It does not change existing tables, so after a model change I delete `instance/app.db` (no migrations in this project).

**Q35. What are CHECK constraints? Which do you use?**
A. Database rules on values: `capacity > 0`, `available_seats >= 0 AND <= capacity`, `end_time > start_time`, `max_marks > 0`, `weightage` between 0 and 100, `marks >= 0`, date order on exams.

**Q36. Which unique constraints exist?**
A. `users.email`, `users.enrollment_no`, `courses.code`, `(exam_id, examiner_id)` in `exam_examiners`, `evaluations.booking_id`, `(evaluation_id, rubric_id)` in `evaluation_scores`.

**Q37. What is a partial unique index and where do you use it?**
A. A unique index that applies only to rows matching a condition. `unique_active_booking` on `(student_id, exam_id) WHERE status = 'booked'` allows only one active booking per student per exam, but lets the student book again after cancelling.

**Q38. Give examples of one-to-many and one-to-one relationships.**
A. One course has many exams (1:N). One booking has at most one evaluation (1:1, enforced by a unique `booking_id`).

**Q39. Why is there an `exam_examiners` table?**
A. An exam can have several examiners and an examiner can work on several exams (many-to-many). The link table stores each pair once.

**Q40. How are enums stored and what does `sa_enum` do?**
A. Python enums (`ExamState`, `BookingStatus`, ...) are mapped to database enums. By default SQLAlchemy stores the member *name*; `sa_enum` uses `values_callable` so the lowercase *value* (`"bookingopen"`) is stored.

**Q41. Why `Numeric` / `Decimal` for marks and weightage instead of float?**
A. Floats can give 0.1 + 0.2 != 0.3 errors. `Decimal` keeps marks exact; the final total is rounded to two decimals.

**Q42. What is `TimestampMixin`?**
A. A small class that adds a `created_at` column to every model that inherits it, so the column is written once.

**Q43. What is a transaction? What do `flush`, `commit` and `rollback` do?**
A. A transaction groups changes so they all succeed or all fail. `flush` sends pending SQL (and assigns ids) without finishing; `commit` makes it permanent; `rollback` undoes it.

**Q44. Why are bookings and history rows never deleted?**
A. A cancelled booking keeps its row with status `cancelled`, so each student's full history is available and audits are possible.

**Q45. What is SQL injection and how do you avoid it?**
A. Attacker-supplied text changes the SQL. SQLAlchemy sends values as bound parameters, never by string concatenation, so input cannot alter the query.

**Q46. Show an example of a join in the project.**
A. `my_bookings()` in `routes/student.py` joins `Booking`, `Slot` and `Exam` and filters by the logged-in student to list their bookings with slot and exam details.

**Q47. Where do you use `outerjoin` and why?**
A. In the evaluations and history lists: a booking may not have an evaluation yet; an outer join still returns the booking with `None` for the evaluation.

**Q48. What does `get_or_404` do?**
A. It loads a row by primary key or aborts with a 404 page if it does not exist.

**Q49. Where is the database file and why?**
A. `instance/app.db`. Flask-SQLAlchemy puts relative SQLite paths in the app's `instance` folder, which is kept out of git.

**Q50. What does `synchronize_session=False` mean in the guarded `update()`?**
A. For a bulk `UPDATE` SQLAlchemy does not try to update objects already loaded in the session; I call `refresh()` afterwards when I need the new value.

**Q51. How are `Date`, `Time` and `DateTime` used?**
A. Slots have a `Date` and two `Time` columns; exam windows and `booking_date` are `DateTime`. SQLite stores them as text and SQLAlchemy converts them to Python objects.

**Q52. Why store the exam windows as `DateTime` and not `Date`?**
A. Deadlines need an exact time (for example booking closes at 18:00), so the date windows are compared with `datetime.now()`.

### D. Authentication and security

**Q53. How are passwords stored?**
A. As salted hashes from `generate_password_hash`. At login `check_password_hash` compares the typed password with the hash. The real password is never stored.

**Q54. Describe the login flow.**
A. Read e-mail (lower-cased) and password -> find the user -> `check_password_hash` -> store `user_id`, `role`, `name` in the session -> redirect to `<role>.dashboard`.

**Q55. How does registration differ for students and examiners?**
A. Students get status `active` and an enrolment number; examiners get status `pending` and a department and must be approved by the Admin.

**Q56. Why is the login error message the same for a wrong e-mail and a wrong password?**
A. A specific message would reveal which e-mails exist (user enumeration).

**Q57. What is object-level authorization? Give examples.**
A. Checking not only the role but ownership of the object: an examiner can open only their own slots and students (`my_slot_or_403`), a student only their own booking or result. This prevents changing an ID in the URL to see someone else's data.

**Q58. Can a student make themselves an Admin?**
A. No. The role is never read from a form; registration allows only `student` or `examiner` from the URL and sets the role on the server.

**Q59. What is CSRF and are you protected?**
A. CSRF makes a logged-in user's browser submit a forged POST. Not implemented yet; the plan is Flask-WTF `CSRFProtect` and a hidden `csrf_token` field in every POST form. I list this as a limitation.

**Q60. What is XSS and how is it prevented here?**
A. Injecting script into a page. Jinja2 auto-escaping is on and I never use `|safe` on user input.

**Q61. What is the `SECRET_KEY` for?**
A. It signs the session cookie. If it is guessed, someone could forge a session. It must be a long random value from the environment in production (mine is a development value).

**Q62. Can a user edit their session cookie to change the role?**
A. No. The cookie is signed; any change invalidates the signature and the session is rejected.

**Q63. Why check the status for examiners at every route?**
A. A rejected or deactivated examiner may still hold a valid session. `examiner_required` reads the status from the database on each request and shows the pending page unless it is `active`.

### E. Business rules and concurrency

**Q64. Explain the exam lifecycle.**
A. Draft -> Slot Creation -> Booking Open -> Closed -> Completed, then results are published. Each step is an Admin button with guards (weightage 100 and an examiner before opening; all bookings evaluated before completing).

**Q65. How do you enforce "examiners create slots only in the creation period"?**
A. `slot_creation_open(exam)`: the exam status must be Slot Creation **and** now must be between `slot_create_start` and `slot_create_end`; the examiner must also be assigned to the exam.

**Q66. Why check both status and dates?**
A. The status is changed by the Admin's button; the dates are a second guard so a forgotten "open" state cannot bypass a deadline.

**Q67. When can an examiner edit or cancel a slot?**
A. Only while the exam is in Slot Creation, before `booking_start`, and only if no student has booked it (`can_change`).

**Q68. Walk me through `booking_service.book`.**
A. Load slot and exam -> booking window open? -> slot not cancelled -> no active booking for the exam -> no clash -> guarded `UPDATE` for a seat -> create booking -> history row -> set Full if seats are 0 -> commit; `IntegrityError` is caught.

**Q69. How is overbooking prevented?**
A. `UPDATE slots SET available_seats = available_seats - 1 WHERE id=? AND available_seats > 0`. If 0 rows were updated the slot is full. A `CHECK(available_seats >= 0)` is a second line of defence.

**Q70. What happens if two students book the last seat at the same time?**
A. SQLite runs the two writes one after another. The first update succeeds (seats 1 -> 0); the second finds `available_seats = 0`, updates 0 rows and gets "slot is full".

**Q71. Why not read the seat count and then write it?**
A. Both requests could read "1 seat left" and both write, giving overbooking. A single conditional `UPDATE` makes the check and the change atomic.

**Q72. How do you prevent a duplicate booking for the same exam?**
A. Three layers: the service looks for an active booking first; the partial unique index rejects a duplicate; the service catches the `IntegrityError`.

**Q73. What is the clash rule?**
A. A student cannot hold two booked slots on the same date whose times overlap: `existing.start < new.end` and `existing.end > new.start`.

**Q74. What happens when a student cancels?**
A. The booking becomes `cancelled`, the slot gets +1 seat, a Full slot becomes Available, a history row is written. Cancelling is allowed only before `booking_end`.

**Q75. What are the slot statuses?**
A. `available`, `full` (no seats), `cancelled` (examiner removed it), `completed` (exam completed).

**Q76. How does the Admin reschedule a booking?**
A. Choose another slot of the same exam with a free seat and no clash. In one transaction the new slot loses a seat, the old one gets it back, `slot_id` and `old_slot_id` are updated, statuses fixed and a `reschedule` history row is written.

**Q77. How does "change examiner" work?**
A. The new examiner must be approved and free at that time. `slots.examiner_id` changes, `exam_examiners` gets a row if needed, and an `examiner_change` history row is written for each booking. The old examiner loses access to that slot, the new one gains it.

**Q78. Why can an examiner not be deactivated with upcoming booked slots?**
A. Their students would be left without an examiner. The Admin must first change the examiner of those slots.

**Q79. Why can a course with exams not be deleted?**
A. Exams reference the course (foreign key). Deleting it would orphan exams; the Admin can deactivate it instead.

**Q80. Why can exams and rubrics be changed only in Draft?**
A. After slots and bookings exist, changing marks or dates would invalidate them.

**Q81. How are rubric weightages validated?**
A. Each is greater than 0 and at most 100; adding a criterion that would push the total above 100 is refused; the exam cannot leave Draft until the total is exactly 100.

**Q82. Why must weightages total 100?**
A. The formula divides the weighted sum by 100, so with a total of 100 a student who scores full marks everywhere gets exactly the exam's `max_marks`.

### F. Evaluation and results

**Q83. Explain the scoring formula with an example.**
A. total = (sum of awarded / max x weightage) / 100 x exam max. Example: max 36; A 40/40 (w 50) and B 28/56 (w 50) -> 50 + 25 = 75 -> 75/100 x 36 = 27.00.

**Q84. Why use `Decimal`?**
A. Exact arithmetic for marks; no floating-point rounding surprises.

**Q85. What happens when an evaluation is submitted?**
A. Evaluation and score rows are saved, `total_marks` is computed, the evaluation becomes `submitted`, the booking becomes `completed` and a `completed` history row is written.

**Q86. Can an examiner change an evaluation later?**
A. Yes, while the exam is still Closed and results are not published; after that it is read-only.

**Q87. When can a student see results?**
A. Only if the evaluation is `submitted` **and** the Admin published the exam's results. Otherwise the page returns 404.

**Q88. Why can the Admin not complete an exam with unevaluated bookings?**
A. Completing means all evaluations are done; results must be based on every booking. The Admin sees "N booking(s) are not evaluated yet".

**Q89. Who can evaluate a booking?**
A. Only the examiner who owns the booking's slot; anyone else gets 403.

**Q90. What if a student does not show up?**
A. There is no "absent" status in this build: the examiner gives 0 marks or the Admin cancels the booking before completing the exam (listed as a limitation).

### G. Templates, features, testing, deployment

**Q91. How are the templates organised?**
A. `base.html` plus one folder per role (`admin/`, `examiner/`, `student/`, `auth/`); the template path is relative to `templates/`.

**Q92. How do search and filters work?**
A. Filter values come from the query string (`request.args`); the route adds `.filter(...)` conditions to a query (for example `Exam.name.ilike('%text%')`) and passes the selected values back to the form.

**Q93. Where is JavaScript used and why is it optional?**
A. Only on the Admin Reports page for Chart.js charts. The same numbers exist in other pages, so nothing important depends on JavaScript.

**Q94. How does the CSV export work?**
A. The route builds the same filtered query as the bookings page, writes rows with Python's `csv` module into a string and returns a `Response` with `text/csv` and a download header.

**Q95. How did you test the project?**
A. Manual walkthrough of the full story plus scripted checks with Flask's test client (pages for every role, booking guards, evaluation maths, 403 / 404 rules, admin overrides, profile) and a clean-install test in a fresh virtual environment.

**Q96. What is `requirements.txt` and why pin versions?**
A. A list of packages for `pip install -r`. Pinned versions make the install reproducible on the grader's machine.

**Q97. What does `.gitignore` do and what is ignored?**
A. It tells git not to track files: `venv/`, `__pycache__/`, `instance/` and `*.db` (generated), `.env` (secrets), editor files, zip files.

**Q98. Why use a virtual environment?**
A. It keeps the project's packages separate from the system Python so versions do not clash.

**Q99. How would you deploy this for real?**
A. Use a production server (Waitress or Gunicorn), `debug=False`, a long random `SECRET_KEY` from an environment variable, HTTPS, a stronger database (PostgreSQL), migrations (Flask-Migrate), CSRF protection and a changed Admin password.

**Q100. What would you improve next, and how did you use AI?**
A. Next: CSRF tokens, JSON API, PDF scorecard, e-mail notifications, pagination, an "absent" status and migrations. AI (Claude) was used to help with design, code, debugging and documentation; I tested the flows, read the code and can explain every part (state your own real use honestly).
