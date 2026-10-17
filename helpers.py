from datetime import datetime
from functools import wraps

from flask import session, redirect, url_for, abort, render_template

from models import User
from models.enums import ExamState


def role_req(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("auth.login"))
            if session.get("role") != role:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def examiner_required(f):
    """Logged in + role examiner + approved by the Admin."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        if session.get("role") != "examiner":
            abort(403)
        user = User.query.get(session["user_id"])
        if user.status.value != "active":
            return render_template("pending.html", status=user.status.value)
        return f(*args, **kwargs)
    return wrapper


# ---------- Slot rules ----------

def slot_creation_open(exam):
    """Slots can be created: exam is in Slot Creation AND now is inside the dates."""
    now = datetime.now()
    return (exam.status == ExamState.SlotCreation
            and exam.slot_create_start <= now <= exam.slot_create_end)


def slots_editable(exam):
    """Slots can be edited or cancelled until booking starts."""
    return (exam.status == ExamState.SlotCreation
            and datetime.now() < exam.booking_start)

def booking_open(exam):
    """Students can book: exam is Booking Open AND now is inside the dates."""
    now = datetime.now()
    return (exam.status == ExamState.BookingOpen
            and exam.booking_start <= now <= exam.booking_end)
