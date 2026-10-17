from datetime import datetime

from flask import (Blueprint, render_template, request, redirect, url_for, flash, session, abort)

from extensions import db
from helpers import examiner_required, slot_creation_open, slots_editable, role_req
from models import (Booking, Course, Evaluation, EvaluationScore, Exam,
                    ExamExaminer, Rubric, Slot, User)
from models.enums import BookingStatus, SlotStatus, ExamState
from services import evaluation_service, profile_service

examiner_bp = Blueprint("examiner", __name__, url_prefix="/examiner")


# ---------- small helpers ----------

def me():
    return session["user_id"]


def assigned_exam_or_403(exam_id):
    """The exam must exist AND be assigned to the logged-in examiner."""
    exam = Exam.query.get_or_404(exam_id)
    mine = ExamExaminer.query.filter_by(exam_id=exam.id, examiner_id=me()).first()
    if not mine:
        abort(403)
    return exam


def my_slot_or_403(slot_id):
    slot = Slot.query.get_or_404(slot_id)
    if slot.examiner_id != me():
        abort(403)
    return slot


def booked_count(slot):
    return Booking.query.filter_by(slot_id=slot.id, status=BookingStatus.Booked).count()


def can_change(slot, exam):
    return (slot.status != SlotStatus.Cancelled
            and slots_editable(exam)
            and booked_count(slot) == 0)


def read_slot_form():
    """Read the slot form. Returns (data, error_message)."""
    f = request.form
    try:
        data = {
            "slot_date": datetime.strptime(f["slot_date"], "%Y-%m-%d").date(),
            "start_time": datetime.strptime(f["start_time"], "%H:%M").time(),
            "end_time": datetime.strptime(f["end_time"], "%H:%M").time(),
            "capacity": int(f["capacity"]),
        }
    except (KeyError, ValueError):
        return None, "Please fill all fields correctly"
    if data["end_time"] <= data["start_time"]:
        return None, "End time must be after start time"
    if data["capacity"] <= 0:
        return None, "Capacity must be at least 1"
    return data, None


def has_clash(data, ignore_id=None):
    """Does this examiner already have a slot overlapping this time?"""
    q = Slot.query.filter(
        Slot.examiner_id == me(),
        Slot.slot_date == data["slot_date"],
        Slot.status != SlotStatus.Cancelled,
        Slot.start_time < data["end_time"],
        Slot.end_time > data["start_time"],
    )
    if ignore_id:
        q = q.filter(Slot.id != ignore_id)
    return q.first() is not None


# ---------- Dashboard ----------

@examiner_bp.route("/dashboard")
@examiner_required
def dashboard():
    stats = {
        "exams": ExamExaminer.query.filter_by(examiner_id=me()).count(),
        "slots": Slot.query.filter(Slot.examiner_id == me(),
                                   Slot.status != SlotStatus.Cancelled).count(),
        "booked": (Booking.query
                   .join(Slot, Booking.slot_id == Slot.id)
                   .filter(Slot.examiner_id == me(),
                           Booking.status == BookingStatus.Booked).count()),

                "pending": (Booking.query
                    .join(Slot, Booking.slot_id == Slot.id)
                    .join(Exam, Booking.exam_id == Exam.id)
                    .filter(Slot.examiner_id == me(), Booking.status == BookingStatus.Booked, Exam.status == ExamState.Closed).count()),

    }
    return render_template("examiner/dashboard.html", stats=stats)


# ---------- Exams ----------

@examiner_bp.route("/exams")
@examiner_required
def exams():
    rows = (db.session.query(Exam, Course)
            .join(Course, Exam.course_id == Course.id)
            .join(ExamExaminer, ExamExaminer.exam_id == Exam.id)
            .filter(ExamExaminer.examiner_id == me())
            .order_by(Exam.id.desc()).all())
    return render_template("examiner/exams.html", rows=rows)


@examiner_bp.route("/exams/<int:exam_id>")
@examiner_required
def exam_detail(exam_id):
    exam = assigned_exam_or_403(exam_id)
    course = Course.query.get(exam.course_id)
    rubrics = Rubric.query.filter_by(exam_id=exam.id).all()
    my_slots = (Slot.query.filter_by(exam_id=exam.id, examiner_id=me())
                .order_by(Slot.slot_date, Slot.start_time).all())
    return render_template("examiner/exam_detail.html", exam=exam, course=course,
                           rubrics=rubrics, my_slots=my_slots,
                           can_create=slot_creation_open(exam))


# ---------- Slots ----------

@examiner_bp.route("/slots")
@examiner_required
def slots():
    rows = (db.session.query(Slot, Exam)
            .join(Exam, Slot.exam_id == Exam.id)
            .filter(Slot.examiner_id == me())
            .order_by(Slot.slot_date, Slot.start_time).all())
    items = [(slot, exam, can_change(slot, exam)) for slot, exam in rows]
    return render_template("examiner/slots.html", items=items)


@examiner_bp.route("/slots/new", methods=["GET", "POST"])
@examiner_required
def slot_new():
    exam = assigned_exam_or_403(request.args.get("exam", 0, type=int))
    back = redirect(url_for("examiner.exam_detail", exam_id=exam.id))

    if not slot_creation_open(exam):
        flash("Slot creation is not open for this exam right now")
        return back

    if request.method == "POST":
        data, error = read_slot_form()
        if not error and has_clash(data):
            error = "You already have a slot at that time"
        if error:
            flash(error)
            return render_template("examiner/slot_form.html", exam=exam,
                                   slot=None, v=request.form)

        slot = Slot(exam_id=exam.id, examiner_id=me(),
                    available_seats=data["capacity"], **data)
        db.session.add(slot)
        db.session.commit()
        flash("Slot created")
        return back

    return render_template("examiner/slot_form.html", exam=exam, slot=None, v={})


@examiner_bp.route("/slots/<int:slot_id>/edit", methods=["GET", "POST"])
@examiner_required
def slot_edit(slot_id):
    slot = my_slot_or_403(slot_id)
    exam = Exam.query.get(slot.exam_id)

    if not can_change(slot, exam):
        flash("This slot can no longer be changed")
        return redirect(url_for("examiner.slots"))

    if request.method == "POST":
        data, error = read_slot_form()
        if not error and has_clash(data, ignore_id=slot.id):
            error = "You already have a slot at that time"
        if error:
            flash(error)
            return render_template("examiner/slot_form.html", exam=exam,
                                   slot=slot, v=request.form)

        slot.slot_date = data["slot_date"]
        slot.start_time = data["start_time"]
        slot.end_time = data["end_time"]
        slot.capacity = data["capacity"]
        slot.available_seats = data["capacity"]   # nobody booked yet
        db.session.commit()
        flash("Slot updated")
        return redirect(url_for("examiner.slots"))

    v = {
        "slot_date": slot.slot_date.isoformat(),
        "start_time": slot.start_time.strftime("%H:%M"),
        "end_time": slot.end_time.strftime("%H:%M"),
        "capacity": slot.capacity,
    }
    return render_template("examiner/slot_form.html", exam=exam, slot=slot, v=v)


@examiner_bp.route("/slots/<int:slot_id>/cancel", methods=["POST"])
@examiner_required
def slot_cancel(slot_id):
    slot = my_slot_or_403(slot_id)
    exam = Exam.query.get(slot.exam_id)

    if not can_change(slot, exam):
        flash("This slot can no longer be cancelled")
    else:
        slot.status = SlotStatus.Cancelled
        slot.available_seats = 0
        db.session.commit()
        flash("Slot cancelled")
    return redirect(url_for("examiner.slots"))


# ---------- Roster ----------

@examiner_bp.route("/slots/<int:slot_id>/students")
@examiner_required
def slot_students(slot_id):
    slot = my_slot_or_403(slot_id)
    exam = Exam.query.get(slot.exam_id)
    rows = (db.session.query(Booking, User)
            .join(User, Booking.student_id == User.id)
            .filter(Booking.slot_id == slot.id,
                    Booking.status.in_([BookingStatus.Booked, BookingStatus.Completed]))
            .all())
    return render_template("examiner/roster.html", slot=slot, exam=exam, rows=rows)


# ---------- Evaluation ----------

@examiner_bp.route("/evaluations")
@examiner_required
def evaluations():
    rows = (db.session.query(Booking, Slot, Exam, User, Evaluation)
            .join(Slot, Booking.slot_id == Slot.id)
            .join(Exam, Booking.exam_id == Exam.id)
            .join(User, Booking.student_id == User.id)
            .outerjoin(Evaluation, Evaluation.booking_id == Booking.id)
            .filter(Slot.examiner_id == me(),
                    Booking.status.in_([BookingStatus.Booked, BookingStatus.Completed]),
                    Exam.status.in_([ExamState.Closed, ExamState.Completed]))
            .order_by(Booking.status, Slot.slot_date, Slot.start_time).all())
    return render_template("examiner/evaluations.html", rows=rows)


@examiner_bp.route("/evaluate/<int:booking_id>", methods=["GET", "POST"])
@examiner_required
def evaluate(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    slot = my_slot_or_403(booking.slot_id)          # not your student -> 403
    if booking.status == BookingStatus.Cancelled:
        abort(404)

    exam = Exam.query.get(booking.exam_id)
    student = User.query.get(booking.student_id)
    rubrics = Rubric.query.filter_by(exam_id=exam.id).order_by(Rubric.id).all()
    evaluation = Evaluation.query.filter_by(booking_id=booking.id).first()

    scores, remarks = {}, ""
    if evaluation:
        scores = {s.rubric_id: s.marks for s in
                  EvaluationScore.query.filter_by(evaluation_id=evaluation.id)}
        remarks = evaluation.remarks or ""

    if request.method == "POST":
        raw = {r.id: request.form.get("marks_%s" % r.id, "") for r in rubrics}
        ok, message = evaluation_service.submit(
            me(), booking.id, raw, request.form.get("remarks", ""))
        flash(message)
        if ok:
            return redirect(url_for("examiner.evaluations"))
        scores, remarks = raw, request.form.get("remarks", "")   # keep what was typed

    editable = exam.status == ExamState.Closed and not exam.results_published
    return render_template("examiner/evaluate.html", booking=booking, slot=slot,
                           exam=exam, student=student, rubrics=rubrics,
                           evaluation=evaluation, scores=scores, remarks=remarks,
                           editable=editable)


# ---------- Profile ----------

@examiner_bp.route("/profile", methods=["GET", "POST"])
@examiner_required
def profile():
    user = User.query.get(me())
    values = {"name": user.name, "phone": user.phone, "department": user.department}

    if request.method == "POST":
        ok, message = profile_service.update_profile(user, request.form)
        flash(message)
        if ok:
            session["name"] = user.name
            return redirect(url_for("examiner.profile"))
        values = request.form          # keep what was typed

    return render_template("profile.html", user=user, v=values,
                           back=url_for("examiner.dashboard"))
