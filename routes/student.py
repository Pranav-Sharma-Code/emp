from flask import (Blueprint, render_template, request, redirect, url_for, flash, session, abort)

from extensions import db
from helpers import role_req, booking_open
from models import (Booking, BookingHistory, Course, Evaluation, EvaluationScore,
                    Exam, Rubric, Slot, User)
from models.enums import BookingStatus, EvaluationStatus, ExamState, ExamType, SlotStatus
from services import booking_service, profile_service

student_bp = Blueprint("student", __name__, url_prefix="/student")


def me():
    return session["user_id"]


def my_bookings(*conditions):
    """(Booking, Slot, Exam) rows of the logged-in student."""
    return (db.session.query(Booking, Slot, Exam)
            .join(Slot, Booking.slot_id == Slot.id)
            .join(Exam, Booking.exam_id == Exam.id)
            .filter(Booking.student_id == me(), *conditions)
            .order_by(Slot.slot_date, Slot.start_time).all())


@student_bp.route("/dashboard")
@role_req("student")
def dashboard():
    open_exams = [e for e in Exam.query.filter_by(status=ExamState.BookingOpen).all() if booking_open(e)]
    upcoming = my_bookings(Booking.status == BookingStatus.Booked)
    return render_template("student/dashboard.html", open_exams=len(open_exams), upcoming=upcoming)


# ---------- Exams: search + filter ----------

@student_bp.route("/exams")
@role_req("student")
def exams():
    query = (db.session.query(Exam, Course)
             .join(Course, Exam.course_id == Course.id)
             .filter(Exam.status != ExamState.Draft))

    f = {
        "q": request.args.get("q", "").strip(),
        "course": request.args.get("course", 0, type=int),
        "type": request.args.get("type", ""),
        "status": request.args.get("status", ""),
    }
    if f["q"]:
        query = query.filter(Exam.name.ilike("%" + f["q"] + "%"))
    if f["course"]:
        query = query.filter(Exam.course_id == f["course"])
    try:
        query = query.filter(Exam.exam_type == ExamType(f["type"]))
    except ValueError:
        pass
    try:
        query = query.filter(Exam.status == ExamState(f["status"]))
    except ValueError:
        pass

    return render_template(
        "student/exams.html", rows=query.order_by(Exam.id.desc()).all(), f=f,
        courses=Course.query.order_by(Course.code).all(),
        types=[t.value for t in ExamType],
        statuses=[s.value for s in ExamState if s != ExamState.Draft],
    )


@student_bp.route("/exams/<int:exam_id>")
@role_req("student")
def exam_detail(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.status == ExamState.Draft:
        abort(404)
    course = Course.query.get(exam.course_id)

    rows = (db.session.query(Slot, User)
            .join(User, Slot.examiner_id == User.id)
            .filter(Slot.exam_id == exam.id, Slot.status != SlotStatus.Cancelled)
            .order_by(Slot.slot_date, Slot.start_time).all())
    mine = Booking.query.filter_by(student_id=me(), exam_id=exam.id,
                                   status=BookingStatus.Booked).first()
    return render_template(
        "student/exam_detail.html", exam=exam, course=course, rows=rows, mine=mine,
        can_book=booking_open(exam) and mine is None,
        show_slots=exam.status != ExamState.SlotCreation,
    )


# ---------- Book / cancel ----------

@student_bp.route("/slots/<int:slot_id>/book", methods=["POST"])
@role_req("student")
def book(slot_id):
    ok, message = booking_service.book(me(), slot_id)
    flash(message)
    return redirect(url_for("student.bookings") if ok else request.referrer or url_for("student.exams"))


@student_bp.route("/bookings")
@role_req("student")
def bookings():
    rows = my_bookings(Booking.status == BookingStatus.Booked)
    return render_template("student/bookings.html", rows=rows)


@student_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@role_req("student")
def cancel(booking_id):
    ok, message = booking_service.cancel(me(), booking_id)
    flash(message)
    return redirect(url_for("student.bookings"))


# ---------- History ----------

@student_bp.route("/history")
@role_req("student")
def history():
    rows = sorted(my_bookings(), key=lambda r: r[0].id, reverse=True)
    events = (db.session.query(BookingHistory, Exam)
              .join(Booking, BookingHistory.booking_id == Booking.id)
              .join(Exam, Booking.exam_id == Exam.id)
              .filter(Booking.student_id == me())
              .order_by(BookingHistory.id.desc()).all())
    return render_template("student/history.html", rows=rows, events=events)


# ---------- Results ----------

@student_bp.route("/results")
@role_req("student")
def results():
    rows = (db.session.query(Booking, Exam, Evaluation)
            .join(Exam, Booking.exam_id == Exam.id)
            .join(Evaluation, Evaluation.booking_id == Booking.id)
            .filter(Booking.student_id == me(),
                    Exam.results_published.is_(True),
                    Evaluation.status == EvaluationStatus.Submitted)
            .order_by(Booking.id.desc()).all())
    return render_template("student/results.html", rows=rows)


@student_bp.route("/results/<int:booking_id>")
@role_req("student")
def result_detail(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.student_id != me():
        abort(404)
    exam = Exam.query.get(booking.exam_id)
    evaluation = Evaluation.query.filter_by(booking_id=booking.id).first()

    # results are visible only when submitted AND published
    if not (evaluation and exam.results_published
            and evaluation.status == EvaluationStatus.Submitted):
        abort(404)

    scores = (db.session.query(EvaluationScore, Rubric)
              .join(Rubric, EvaluationScore.rubric_id == Rubric.id)
              .filter(EvaluationScore.evaluation_id == evaluation.id)
              .order_by(Rubric.id).all())
    return render_template("student/result_detail.html", exam=exam,
                           evaluation=evaluation, scores=scores)


# ---------- Profile ----------

@student_bp.route("/profile", methods=["GET", "POST"])
@role_req("student")
def profile():
    user = User.query.get(me())
    values = {"name": user.name, "phone": user.phone, "department": user.department}

    if request.method == "POST":
        ok, message = profile_service.update_profile(user, request.form)
        flash(message)
        if ok:
            session["name"] = user.name
            return redirect(url_for("student.profile"))
        values = request.form          # keep what was typed

    return render_template("profile.html", user=user, v=values,
                           back=url_for("student.dashboard"))
