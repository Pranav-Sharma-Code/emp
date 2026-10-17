import csv
import io
from collections import Counter
from datetime import datetime

from flask import (render_template, request, redirect, url_for, flash,
                   abort, Response, session)
from sqlalchemy import func, or_

from extensions import db
from helpers import role_req
from models import (Booking, BookingHistory, Course, Evaluation, Exam, Slot, User)
from models.enums import BookingStatus, ExamState, SlotStatus, UserRole, UserStatus
from routes.admin import admin_bp
from services import admin_service


def parse_date(text):
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


# ---------- Students ----------

@admin_bp.route("/students")
@role_req("admin")
def students():
    q = request.args.get("q", "").strip()
    query = User.query.filter_by(role=UserRole.Student)
    if q:
        like = "%" + q + "%"
        query = query.filter(or_(User.name.ilike(like), User.email.ilike(like),
                                 User.enrollment_no.ilike(like)))
    counts = dict(db.session.query(Booking.student_id, func.count(Booking.id))
                  .group_by(Booking.student_id).all())
    return render_template("admin/students.html", people=query.order_by(User.name).all(),
                           counts=counts, q=q)


@admin_bp.route("/students/<int:user_id>")
@role_req("admin")
def student_detail(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != UserRole.Student:
        abort(404)
    rows = (db.session.query(Booking, Slot, Exam, Evaluation)
            .join(Slot, Booking.slot_id == Slot.id)
            .join(Exam, Booking.exam_id == Exam.id)
            .outerjoin(Evaluation, Evaluation.booking_id == Booking.id)
            .filter(Booking.student_id == user.id)
            .order_by(Booking.id.desc()).all())
    events = (db.session.query(BookingHistory, Exam)
              .join(Booking, BookingHistory.booking_id == Booking.id)
              .join(Exam, Booking.exam_id == Exam.id)
              .filter(Booking.student_id == user.id)
              .order_by(BookingHistory.id.desc()).all())
    return render_template("admin/student_detail.html", user=user, rows=rows, events=events)


# ---------- Examiner profile ----------

@admin_bp.route("/examiners/<int:user_id>")
@role_req("admin")
def examiner_detail(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != UserRole.Examiner:
        abort(404)
    rows = (db.session.query(Slot, Exam)
            .join(Exam, Slot.exam_id == Exam.id)
            .filter(Slot.examiner_id == user.id)
            .order_by(Slot.slot_date, Slot.start_time).all())
    counts = dict(db.session.query(Booking.slot_id, func.count(Booking.id))
                  .filter(Booking.status != BookingStatus.Cancelled)
                  .group_by(Booking.slot_id).all())
    return render_template("admin/examiner_detail.html", user=user, rows=rows, counts=counts)


# ---------- Slots ----------

@admin_bp.route("/slots")
@role_req("admin")
def slots():
    exam_id = request.args.get("exam", 0, type=int)
    examiner_id = request.args.get("examiner", 0, type=int)
    status = request.args.get("status", "")

    query = (db.session.query(Slot, Exam, User)
             .join(Exam, Slot.exam_id == Exam.id)
             .join(User, Slot.examiner_id == User.id))
    if exam_id:
        query = query.filter(Slot.exam_id == exam_id)
    if examiner_id:
        query = query.filter(Slot.examiner_id == examiner_id)
    try:
        query = query.filter(Slot.status == SlotStatus(status))
    except ValueError:
        pass

    return render_template(
        "admin/slots.html", rows=query.order_by(Slot.slot_date, Slot.start_time).all(),
        exams=Exam.query.order_by(Exam.name).all(),
        examiners=User.query.filter_by(role=UserRole.Examiner).order_by(User.name).all(),
        statuses=[s.value for s in SlotStatus],
        f={"exam": exam_id, "examiner": examiner_id, "status": status},
    )


@admin_bp.route("/slots/<int:slot_id>")
@role_req("admin")
def slot_detail(slot_id):
    slot = Slot.query.get_or_404(slot_id)
    exam = Exam.query.get(slot.exam_id)
    examiner = User.query.get(slot.examiner_id)
    bookings = (db.session.query(Booking, User)
                .join(User, Booking.student_id == User.id)
                .filter(Booking.slot_id == slot.id).all())
    others = (User.query.filter(User.role == UserRole.Examiner,
                                User.status == UserStatus.Active,
                                User.id != slot.examiner_id)
              .order_by(User.name).all())
    return render_template("admin/slot_detail.html", slot=slot, exam=exam,
                           examiner=examiner, bookings=bookings, others=others)


@admin_bp.route("/slots/<int:slot_id>/change-examiner", methods=["POST"])
@role_req("admin")
def slot_change_examiner(slot_id):
    Slot.query.get_or_404(slot_id)
    examiner_id = request.form.get("examiner_id", 0, type=int)
    ok, message = admin_service.change_examiner(slot_id, examiner_id, session["user_id"])
    flash(message)
    return redirect(url_for("admin.slot_detail", slot_id=slot_id))


# ---------- Bookings ----------

def bookings_query():
    """Filtered (Booking, Slot, Exam, User) query used by the list and the CSV."""
    exam_id = request.args.get("exam", 0, type=int)
    status = request.args.get("status", "")
    query = (db.session.query(Booking, Slot, Exam, User)
             .join(Slot, Booking.slot_id == Slot.id)
             .join(Exam, Booking.exam_id == Exam.id)
             .join(User, Booking.student_id == User.id))
    if exam_id:
        query = query.filter(Booking.exam_id == exam_id)
    try:
        query = query.filter(Booking.status == BookingStatus(status))
    except ValueError:
        pass
    return query.order_by(Booking.id.desc()), {"exam": exam_id, "status": status}


@admin_bp.route("/bookings")
@role_req("admin")
def bookings():
    query, f = bookings_query()
    return render_template("admin/bookings.html", rows=query.all(), f=f,
                           exams=Exam.query.order_by(Exam.name).all(),
                           statuses=[s.value for s in BookingStatus])


@admin_bp.route("/bookings/export.csv")
@role_req("admin")
def bookings_export():
    query, _ = bookings_query()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["booking_id", "student", "email", "exam", "slot_date",
                     "start", "end", "status", "booked_on"])
    for b, slot, exam, student in query.all():
        writer.writerow([b.id, student.name, student.email, exam.name, slot.slot_date,
                         slot.start_time.strftime("%H:%M"), slot.end_time.strftime("%H:%M"),
                         b.status.value, b.booking_date.strftime("%Y-%m-%d %H:%M")])
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=bookings.csv"})


@admin_bp.route("/bookings/<int:booking_id>")
@role_req("admin")
def booking_detail(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    slot = Slot.query.get(booking.slot_id)
    exam = Exam.query.get(booking.exam_id)
    student = User.query.get(booking.student_id)
    options = (Slot.query.filter(Slot.exam_id == exam.id, Slot.id != slot.id,
                                 Slot.status.in_([SlotStatus.Available]),
                                 Slot.available_seats > 0)
               .order_by(Slot.slot_date, Slot.start_time).all())
    events = (BookingHistory.query.filter_by(booking_id=booking.id)
              .order_by(BookingHistory.id).all())
    return render_template("admin/booking_detail.html", booking=booking, slot=slot,
                           exam=exam, student=student, options=options, events=events)


@admin_bp.route("/bookings/<int:booking_id>/reschedule", methods=["POST"])
@role_req("admin")
def booking_reschedule(booking_id):
    Booking.query.get_or_404(booking_id)
    new_slot_id = request.form.get("slot_id", 0, type=int)
    ok, message = admin_service.reschedule(booking_id, new_slot_id, session["user_id"])
    flash(message)
    return redirect(url_for("admin.booking_detail", booking_id=booking_id))


@admin_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@role_req("admin")
def booking_cancel(booking_id):
    Booking.query.get_or_404(booking_id)
    ok, message = admin_service.cancel_booking(booking_id, session["user_id"])
    flash(message)
    return redirect(url_for("admin.booking_detail", booking_id=booking_id))


# ---------- Search ----------

@admin_bp.route("/search")
@role_req("admin")
def search():
    q = request.args.get("q", "").strip()
    kind = request.args.get("type", "all")
    results = {"students": [], "examiners": [], "exams": [], "bookings": []}

    if q:
        like = "%" + q + "%"
        number = int(q) if q.isdigit() else None

        def people(role):
            cond = [User.name.ilike(like), User.email.ilike(like)]
            if role == UserRole.Student:
                cond.append(User.enrollment_no.ilike(like))
            if number is not None:
                cond.append(User.id == number)
            return User.query.filter(User.role == role, or_(*cond)).limit(50).all()

        if kind in ("all", "students"):
            results["students"] = people(UserRole.Student)
        if kind in ("all", "examiners"):
            results["examiners"] = people(UserRole.Examiner)
        if kind in ("all", "exams"):
            cond = [Exam.name.ilike(like)]
            if number is not None:
                cond.append(Exam.id == number)
            results["exams"] = Exam.query.filter(or_(*cond)).limit(50).all()
        if kind in ("all", "bookings"):
            cond = [User.name.ilike(like), Exam.name.ilike(like)]
            if number is not None:
                cond.append(Booking.id == number)
            results["bookings"] = (db.session.query(Booking, User, Exam, Slot)
                                   .join(User, Booking.student_id == User.id)
                                   .join(Exam, Booking.exam_id == Exam.id)
                                   .join(Slot, Booking.slot_id == Slot.id)
                                   .filter(or_(*cond))
                                   .order_by(Booking.id.desc()).limit(50).all())

    total = sum(len(v) for v in results.values())
    return render_template("admin/search.html", q=q, kind=kind, results=results, total=total)


# ---------- History (past exams) ----------

@admin_bp.route("/history")
@role_req("admin")
def history():
    course_id = request.args.get("course", 0, type=int)
    date_from = parse_date(request.args.get("from", ""))
    date_to = parse_date(request.args.get("to", ""))

    query = (db.session.query(Booking, Slot, Exam, Course, User, Evaluation)
             .join(Slot, Booking.slot_id == Slot.id)
             .join(Exam, Booking.exam_id == Exam.id)
             .join(Course, Exam.course_id == Course.id)
             .join(User, Booking.student_id == User.id)
             .outerjoin(Evaluation, Evaluation.booking_id == Booking.id)
             .filter(Exam.status == ExamState.Completed))
    if course_id:
        query = query.filter(Exam.course_id == course_id)
    if date_from:
        query = query.filter(Slot.slot_date >= date_from)
    if date_to:
        query = query.filter(Slot.slot_date <= date_to)

    return render_template(
        "admin/history.html", rows=query.order_by(Slot.slot_date.desc()).all(),
        courses=Course.query.order_by(Course.code).all(),
        f={"course": course_id, "from": request.args.get("from", ""),
           "to": request.args.get("to", "")},
    )


# ---------- Reports (Chart.js) ----------

@admin_bp.route("/reports")
@role_req("admin")
def reports():
    day = func.date(Booking.booking_date)
    trend = (db.session.query(day, func.count(Booking.id))
             .group_by(day).order_by(day).all())

    status_counts = Counter(s.value for (s,) in db.session.query(Booking.status).all())

    examiners = User.query.filter_by(role=UserRole.Examiner).order_by(User.name).all()
    slot_counts = dict(db.session.query(Slot.examiner_id, func.count(Slot.id))
                       .filter(Slot.status != SlotStatus.Cancelled)
                       .group_by(Slot.examiner_id).all())
    booking_counts = dict(db.session.query(Slot.examiner_id, func.count(Booking.id))
                          .join(Booking, Booking.slot_id == Slot.id)
                          .filter(Booking.status != BookingStatus.Cancelled)
                          .group_by(Slot.examiner_id).all())

    active = status_counts["booked"] + status_counts["completed"]
    rate = round(100 * status_counts["completed"] / active) if active else 0

    data = {
        "trend": {"labels": [str(d) for d, _ in trend], "values": [n for _, n in trend]},
        "workload": {"labels": [e.name for e in examiners],
                     "slots": [slot_counts.get(e.id, 0) for e in examiners],
                     "bookings": [booking_counts.get(e.id, 0) for e in examiners]},
        "status": {"labels": list(status_counts.keys()), "values": list(status_counts.values())},
    }
    return render_template("admin/reports.html", data=data, rate=rate,
                           total=sum(status_counts.values()))
