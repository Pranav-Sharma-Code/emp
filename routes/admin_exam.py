from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import render_template, request, redirect, url_for, flash, abort

from extensions import db
from helpers import role_req
from models import User, Course, Exam, ExamExaminer, Rubric
from models.enums import UserRole, UserStatus, ExamType, ExamState
from routes.admin import admin_bp

DATE_FMT = "%Y-%m-%dT%H:%M"      # format of <input type="datetime-local">
DATE_FIELDS = ["slot_create_start", "slot_create_end", "booking_start", "booking_end"]

# action name -> (from status, to status)
STEPS = {
    "open-slot-creation": (ExamState.Draft, ExamState.SlotCreation),
    "open-booking": (ExamState.SlotCreation, ExamState.BookingOpen),
    "close-booking": (ExamState.BookingOpen, ExamState.Closed),
    "complete": (ExamState.Closed, ExamState.Completed),
}

# status shown now -> (action, button text) for the next step
NEXT_BUTTON = {
    "draft": ("open-slot-creation", "Open slot creation"),
    "slotcreation": ("open-booking", "Close slot creation and open booking"),
    "bookingopen": ("close-booking", "Close booking"),
    "closed": ("complete", "Mark as completed"),
}


def read_exam_form():
    """Read the exam form. Returns (data, error_message)."""
    f = request.form
    try:
        data = {
            "course_id": int(f["course_id"]),
            "name": f["name"].strip(),
            "exam_type": ExamType(f["exam_type"]),
            "duration_minutes": int(f["duration_minutes"]),
            "max_marks": int(f["max_marks"]),
        }
        for field in DATE_FIELDS:
            data[field] = datetime.strptime(f[field], DATE_FMT)
    except (KeyError, ValueError):
        return None, "Please fill all fields correctly"

    if not data["name"] or data["duration_minutes"] <= 0 or data["max_marks"] <= 0:
        return None, "Name, duration and marks must be valid"
    if data["slot_create_end"] < data["slot_create_start"]:
        return None, "Slot creation end must be after its start"
    if data["booking_end"] <= data["booking_start"]:
        return None, "Booking end must be after its start"
    if data["booking_start"] < data["slot_create_end"]:
        return None, "Booking must start after slot creation ends"
    return data, None


def exam_to_form(exam):
    """Turn an Exam row into a dict the form can show."""
    v = {
        "course_id": exam.course_id,
        "name": exam.name,
        "exam_type": exam.exam_type.value,
        "duration_minutes": exam.duration_minutes,
        "max_marks": exam.max_marks,
    }
    for field in DATE_FIELDS:
        v[field] = getattr(exam, field).strftime(DATE_FMT)
    return v


def show_form(exam, values):
    courses = Course.query.filter_by(status=True).all()
    types = [t.value for t in ExamType]
    return render_template("admin/exam_form.html", exam=exam, v=values,
                           courses=courses, types=types)


# ---------- List / create / edit / delete ----------

@admin_bp.route("/exams")
@role_req("admin")
def exams():
    rows = (db.session.query(Exam, Course)
            .join(Course, Exam.course_id == Course.id)
            .order_by(Exam.id.desc()).all())
    return render_template("admin/exams.html", rows=rows)


@admin_bp.route("/exams/new", methods=["GET", "POST"])
@role_req("admin")
def exam_new():
    if request.method == "POST":
        data, error = read_exam_form()
        if error:
            flash(error)
            return show_form(None, request.form)
        exam = Exam(**data)
        db.session.add(exam)
        db.session.commit()
        flash("Exam created. Now add rubrics and examiners.")
        return redirect(url_for("admin.exam_detail", exam_id=exam.id))
    return show_form(None, {})


@admin_bp.route("/exams/<int:exam_id>/edit", methods=["GET", "POST"])
@role_req("admin")
def exam_edit(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.status != ExamState.Draft:
        flash("Only Draft exams can be edited")
        return redirect(url_for("admin.exam_detail", exam_id=exam.id))

    if request.method == "POST":
        data, error = read_exam_form()
        if error:
            flash(error)
            return show_form(exam, request.form)
        for key, value in data.items():
            setattr(exam, key, value)
        db.session.commit()
        flash("Exam updated")
        return redirect(url_for("admin.exam_detail", exam_id=exam.id))
    return show_form(exam, exam_to_form(exam))


@admin_bp.route("/exams/<int:exam_id>/delete", methods=["POST"])
@role_req("admin")
def exam_delete(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.status != ExamState.Draft:
        flash("Only Draft exams can be deleted")
        return redirect(url_for("admin.exam_detail", exam_id=exam.id))
    Rubric.query.filter_by(exam_id=exam.id).delete()
    ExamExaminer.query.filter_by(exam_id=exam.id).delete()
    db.session.delete(exam)
    db.session.commit()
    flash("Exam deleted")
    return redirect(url_for("admin.exams"))


# ---------- Detail page ----------

@admin_bp.route("/exams/<int:exam_id>")
@role_req("admin")
def exam_detail(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    course = Course.query.get(exam.course_id)
    rubrics = Rubric.query.filter_by(exam_id=exam.id).all()
    total = sum((r.weightage for r in rubrics), Decimal(0))

    assigned = (User.query
                .join(ExamExaminer, ExamExaminer.examiner_id == User.id)
                .filter(ExamExaminer.exam_id == exam.id).all())
    assigned_ids = [u.id for u in assigned]
    available = User.query.filter(
        User.role == UserRole.Examiner,
        User.status == UserStatus.Active,
        ~User.id.in_(assigned_ids),
    ).all()

    return render_template(
        "admin/exam_detail.html", exam=exam, course=course, rubrics=rubrics,
        total=total, assigned=assigned, available=available,
        step=NEXT_BUTTON.get(exam.status.value),
    )


# ---------- Rubrics ----------

@admin_bp.route("/exams/<int:exam_id>/rubrics/new", methods=["POST"])
@role_req("admin")
def rubric_new(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    back = redirect(url_for("admin.exam_detail", exam_id=exam.id))

    if exam.status != ExamState.Draft:
        flash("Rubrics can only be changed while the exam is Draft")
        return back
    try:
        name = request.form["criterion_name"].strip()
        max_marks = int(request.form["max_marks"])
        weightage = Decimal(request.form["weightage"])
    except (KeyError, ValueError, InvalidOperation):
        flash("Please fill the rubric fields correctly")
        return back
    if not name or max_marks <= 0 or not (0 < weightage <= 100):
        flash("Invalid rubric values")
        return back

    current = sum((r.weightage for r in Rubric.query.filter_by(exam_id=exam.id)),
                  Decimal(0))
    if current + weightage > 100:
        flash("Total weightage cannot be more than 100")
        return back

    db.session.add(Rubric(exam_id=exam.id, criterion_name=name,
                          max_marks=max_marks, weightage=weightage))
    db.session.commit()
    return back


@admin_bp.route("/exams/<int:exam_id>/rubrics/<int:rubric_id>/delete", methods=["POST"])
@role_req("admin")
def rubric_delete(exam_id, rubric_id):
    exam = Exam.query.get_or_404(exam_id)
    rubric = Rubric.query.get_or_404(rubric_id)
    if rubric.exam_id != exam.id:
        abort(404)
    if exam.status != ExamState.Draft:
        flash("Rubrics can only be changed while the exam is Draft")
    else:
        db.session.delete(rubric)
        db.session.commit()
    return redirect(url_for("admin.exam_detail", exam_id=exam.id))


# ---------- Assign examiners ----------

@admin_bp.route("/exams/<int:exam_id>/examiners/add", methods=["POST"])
@role_req("admin")
def examiner_assign(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    user = User.query.get_or_404(int(request.form["examiner_id"]))
    already = ExamExaminer.query.filter_by(exam_id=exam.id, examiner_id=user.id).first()

    if user.role != UserRole.Examiner or user.status != UserStatus.Active:
        flash("Only approved examiners can be assigned")
    elif not already:
        db.session.add(ExamExaminer(exam_id=exam.id, examiner_id=user.id))
        db.session.commit()
    return redirect(url_for("admin.exam_detail", exam_id=exam.id))


@admin_bp.route("/exams/<int:exam_id>/examiners/<int:user_id>/remove", methods=["POST"])
@role_req("admin")
def examiner_remove(exam_id, user_id):
    ExamExaminer.query.filter_by(exam_id=exam_id, examiner_id=user_id).delete()
    db.session.commit()
    return redirect(url_for("admin.exam_detail", exam_id=exam_id))


# ---------- Status buttons ----------

@admin_bp.route("/exams/<int:exam_id>/status/<action>", methods=["POST"])
@role_req("admin")
def exam_status(exam_id, action):
    exam = Exam.query.get_or_404(exam_id)
    back = redirect(url_for("admin.exam_detail", exam_id=exam.id))

    if action == "publish-results":
        if exam.status == ExamState.Completed and not exam.results_published:
            exam.results_published = True
            db.session.commit()
            flash("Results published")
        else:
            flash("Results can be published only after the exam is Completed")
        return back

    if action not in STEPS:
        abort(404)
    from_state, to_state = STEPS[action]
    if exam.status != from_state:
        flash("This step is not allowed right now")
        return back

    if action == "open-slot-creation":
        total = sum((r.weightage for r in Rubric.query.filter_by(exam_id=exam.id)),
                    Decimal(0))
        if total != 100:
            flash("Rubric weightage must total 100 first")
            return back
        if not ExamExaminer.query.filter_by(exam_id=exam.id).first():
            flash("Assign at least one examiner first")
            return back

    exam.status = to_state
    db.session.commit()
    flash(f"Exam is now {to_state.value}")
    return back
