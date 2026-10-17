from sqlalchemy import CheckConstraint

from extensions import db
from models.enums import SlotStatus, sa_enum
from models.mixins import TimestampMixin


class Slot(TimestampMixin, db.Model):
    __tablename__ = "slots"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    slot_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)
    status = db.Column(sa_enum(SlotStatus), nullable=False, default=SlotStatus.Available)
    __table_args__ = (
        CheckConstraint("capacity > 0", name="check_slot_capacity"),
        CheckConstraint("available_seats >= 0 AND available_seats <= capacity", name="check_available_seats"),
        CheckConstraint("end_time > start_time", name="check_slot_time"),
    )
