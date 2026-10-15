from sqlalchemy import CheckConstraint

from extensions import db
from models.enums import Examtype, ExamState


class exams_table(db.Model):
    __tablename__ = "exams"
    id = db.Column(db.Integer, autoincrement=True, unique=True, primary_key=True)
    course_id = db.Column(db.Integer, forign_key=True)
    name = db.Column(db.String(100), nullable=False)
    exam_type = db.Column(db.Enum(Examtype), nullable=False, default=Examtype.Viva)
    duration = db.Column(db.time, nullable=False)
    max_marks = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum(ExamState), nullable=False, default=ExamState.SlotCreation)
    slot_create_start = db.Column(db.date, nullable=False)
    slot_create_end = db.Column(db.date, nullable=False)
    booking_start = db.Column(db.date, nullable=False)
    booking_end = db.Column(db.date, nullable=False)
    result = db.Column(db.Boolen, nullable=True)
    __table_args__ = (
        CheckConstraint("duration > 0", name="check_exam_duration"),
        CheckConstraint("max_marks > 0", name="check_exam_max_marks"),
        CheckConstraint("slot_create_end >= slot_create_start", name="check_slot_creation_dates"),
        CheckConstraint("bookings_end > booking_start", name="check_booking_dates"),
    )
