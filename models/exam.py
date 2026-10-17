from sqlalchemy import CheckConstraint

from extensions import db
from models.enums import ExamState, ExamType, sa_enum
from models.mixins import TimestampMixin


class Exam(TimestampMixin, db.Model):
    __tablename__ = "exams"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    exam_type = db.Column(sa_enum(ExamType), nullable=False, default=ExamType.Viva)
    duration_minutes = db.Column(db.Integer, nullable=False)
    max_marks = db.Column(db.Integer, nullable=False)
    status = db.Column(sa_enum(ExamState), nullable=False, default=ExamState.Draft)
    slot_create_start = db.Column(db.DateTime, nullable=False)
    slot_create_end = db.Column(db.DateTime, nullable=False)
    booking_start = db.Column(db.DateTime, nullable=False)
    booking_end = db.Column(db.DateTime, nullable=False)
    results_published = db.Column(db.Boolean, nullable=False, default=False)
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="check_exam_duration"),
        CheckConstraint("max_marks > 0", name="check_exam_max_marks"),
        CheckConstraint("slot_create_end >= slot_create_start", name="check_slot_creation_dates"),
        CheckConstraint("booking_end > booking_start", name="check_booking_dates"),
    )
