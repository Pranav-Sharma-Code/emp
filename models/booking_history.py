from extensions import db
from models.mixins import TimestampMixin


class BookingHistory(TimestampMixin, db.Model):
    __tablename__ = "booking_history"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    action = db.Column(db.String(30), nullable=False)  # book, cancel, reschedule, ...
    from_slot_id = db.Column(db.Integer, db.ForeignKey("slots.id"), nullable=True)
    to_slot_id = db.Column(db.Integer, db.ForeignKey("slots.id"), nullable=True)
    acted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    note = db.Column(db.String(200))
