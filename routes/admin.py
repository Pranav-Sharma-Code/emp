from datetime import date
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, abort)

from extensions import db
from models import Slot, Booking
from models.enums import SlotStatus, BookingStatus
from helpers import role_req
from models import User, Course, Exam
from models.enums import UserRole, UserStatus

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@role_req("admin")
def dashboard():
    stats = {
        "pending": User.query.filter_by(role=UserRole.Examiner, status=UserStatus.Pending).count(),
        "examiners": User.query.filter_by(role=UserRole.Examiner, status=UserStatus.Active).count(),
        "students": User.query.filter_by(role=UserRole.Student).count(),
        "courses": Course.query.count(),
        "exams": Exam.query.count(),
    }
    return render_template("admin/dashboard.html", stats=stats)


# ---------- Examiners ----------

@admin_bp.route("/examiners")
@role_req("admin")
def examiners():
    people = User.query.filter_by(role=UserRole.Examiner).all()
    return render_template("admin/examiners.html", people=people)


@admin_bp.route("/examiners/<int:user_id>/<action>", methods=["POST"])
@role_req("admin")
def examiner_action(user_id, action):
    user = User.query.get_or_404(user_id)
    if user.role != UserRole.Examiner:
        abort(404)

    new_status = {
        "approve": UserStatus.Active,
        "reject": UserStatus.Rejected,
        "deactivate": UserStatus.Inactive,
        "reactivate": UserStatus.Active,
    }.get(action)
    if new_status is None:
        abort(404)

    if action == "deactivate":
        busy = (Slot.query
                .join(Booking, Booking.slot_id == Slot.id)
                .filter(Slot.examiner_id == user.id,
                        Slot.slot_date >= date.today(),
                        Slot.status != SlotStatus.Cancelled,
                        Booking.status == BookingStatus.Booked)
                .first())
        if busy:
            flash("Cannot deactivate: this examiner has upcoming slots with bookings. "
                  "Change the examiner of those slots first.")
            return redirect(url_for("admin.examiners"))

    user.status = new_status
    db.session.commit()
    flash(f"{user.name} is now {new_status.value}")
    return redirect(url_for("admin.examiners"))


# ---------- Courses ----------

@admin_bp.route("/courses")
@role_req("admin")
def courses():
    items = Course.query.order_by(Course.id.desc()).all()
    return render_template("admin/courses.html", items=items)


@admin_bp.route("/courses/new", methods=["GET", "POST"])
@role_req("admin")
def course_new():
    if request.method == "POST":
        code = request.form["code"].strip().upper()
        if Course.query.filter_by(code=code).first():
            flash("This course code already exists")
            return redirect(url_for("admin.course_new"))

        course = Course(
            code=code,
            name=request.form["name"].strip(),
            description=request.form.get("description", "").strip(),
        )
        db.session.add(course)
        db.session.commit()
        flash("Course created")
        return redirect(url_for("admin.courses"))

    return render_template("admin/course_form.html", course=None)


@admin_bp.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@role_req("admin")
def course_edit(course_id):
    course = Course.query.get_or_404(course_id)

    if request.method == "POST":
        code = request.form["code"].strip().upper()
        other = Course.query.filter_by(code=code).first()
        if other and other.id != course.id:
            flash("This course code already exists")
            return redirect(url_for("admin.course_edit", course_id=course.id))

        course.code = code
        course.name = request.form["name"].strip()
        course.description = request.form.get("description", "").strip()
        db.session.commit()
        flash("Course updated")
        return redirect(url_for("admin.courses"))

    return render_template("admin/course_form.html", course=course)


@admin_bp.route("/courses/<int:course_id>/toggle", methods=["POST"])
@role_req("admin")
def course_toggle(course_id):
    course = Course.query.get_or_404(course_id)
    course.status = not course.status
    db.session.commit()
    return redirect(url_for("admin.courses"))


@admin_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@role_req("admin")
def course_delete(course_id):
    course = Course.query.get_or_404(course_id)
    if Exam.query.filter_by(course_id=course.id).first():
        flash("Cannot delete: this course has exams")
    else:
        db.session.delete(course)
        db.session.commit()
        flash("Course deleted")
    return redirect(url_for("admin.courses"))
