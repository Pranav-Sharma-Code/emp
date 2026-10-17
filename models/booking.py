from sqlalchemy import Index, text

from extensions import db
from models.enums import BookingStatus, sa_enum
from models.mixins import TimestampMixin


class Booking(TimestampMixin, db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey("slots.id"), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    booking_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(sa_enum(BookingStatus), nullable=False, default=BookingStatus.Booked)
    old_slot_id = db.Column(db.Integer, db.ForeignKey("slots.id"), nullable=True)
    __table_args__ = (
        # one active booking per student per exam
        Index(
            "unique_active_booking",
            "student_id",
            "exam_id",
            unique=True,
            sqlite_where=text("status = 'booked'"),
        ),
    )
