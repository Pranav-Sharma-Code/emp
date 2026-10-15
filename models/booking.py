from sqlalchemy import UniqueConstraint

from extensions import db
from models.enums import BookingStatus


class bookings_table(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, autoincrement=True, unique=True, primary_key=True)
    student_id = db.Column(db.Integer, forign_key=True)
    slot_id = db.Column(db.Integer, forign_key=True)
    booking_date = db.Column(db.date, nullable=False)
    status = db.Column(db.Enum(BookingStatus), nullable=False, default=BookingStatus.Completed)
    old_slot_id = db.Column(db.Integer)
    __table_args__ = (
        UniqueConstraint("student_id", "slot_id", name="unique_student_slot"),
    )
