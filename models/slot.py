from sqlalchemy import CheckConstraint

from extensions import db
from models.enums import SlotsStatus


class slots_table(db.Model):
    __tablename__ = "slots"
    id = db.Column(db.Integer, autoincrement=True, unique=True, primary_key=True)
    exam_id = db.Column(db.Integer, forign_key=True)
    examiner_id = db.Column(db.Integer, forign_key=True)
    slot_date = db.Column(db.date, nullable=False)
    start_time = db.Column(db.time, nullable=False)
    end_time = db.Column(db.time, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    available_seats = db.Column(db.Integer)
    status = db.Column(db.Enum(SlotsStatus), nullable=True, default=SlotsStatus.Available)
    __table_args__ = (
        CheckConstraint("capacity > 0", name="check_slot_capacity"),
        CheckConstraint("available_seats >= 0 AND available_seats <= capacity", name="check_available_seats"),
        CheckConstraint("end_time > start_time", name="check_slot_time"),
    )
