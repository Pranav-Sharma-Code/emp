from datetime import datetime

from sqlalchemy.exc import IntegrityError

from extensions import db
from helpers import booking_open
from models import Booking, BookingHistory, Exam, Slot
from models.enums import BookingStatus, SlotStatus


def _log(booking, action, acted_by, from_slot=None, to_slot=None):
    """Write one line in the booking history. Rows are never deleted."""
    db.session.add(BookingHistory(
        booking_id=booking.id, action=action, acted_by=acted_by,
        from_slot_id=from_slot, to_slot_id=to_slot,
    ))


def _clashes(student_id, slot):
    """Does the student already have a booked slot at the same time?"""
    return (Booking.query
            .join(Slot, Booking.slot_id == Slot.id)
            .filter(Booking.student_id == student_id,
                    Booking.status == BookingStatus.Booked,
                    Slot.slot_date == slot.slot_date,
                    Slot.start_time < slot.end_time,
                    Slot.end_time > slot.start_time)
            .first() is not None)


def book(student_id, slot_id):
    """Returns (True/False, message)."""
    slot = Slot.query.get(slot_id)
    if slot is None:
        return False, "Slot not found"
    exam = Exam.query.get(slot.exam_id)

    if not booking_open(exam):
        return False, "Booking is not open for this exam"
    if slot.status == SlotStatus.Cancelled:
        return False, "This slot was cancelled"

    already = Booking.query.filter_by(student_id=student_id, exam_id=exam.id,
                                      status=BookingStatus.Booked).first()
    if already:
        return False, "You already have a booking for this exam"
    if _clashes(student_id, slot):
        return False, "You have another booking at the same time"

    try:
        # take one seat ONLY IF a seat is left (this is the overbooking guard)
        taken = (Slot.query
                 .filter(Slot.id == slot.id, Slot.available_seats > 0,
                         Slot.status != SlotStatus.Cancelled)
                 .update({Slot.available_seats: Slot.available_seats - 1},
                         synchronize_session=False))
        if taken == 0:
            db.session.rollback()
            return False, "Sorry, this slot is full"

        booking = Booking(student_id=student_id, slot_id=slot.id, exam_id=exam.id,
                          booking_date=datetime.now(), status=BookingStatus.Booked)
        db.session.add(booking)
        db.session.flush()                      # gives booking.id
        _log(booking, "book", student_id, to_slot=slot.id)

        db.session.refresh(slot)
        if slot.available_seats == 0:
            slot.status = SlotStatus.Full
        db.session.commit()
    except IntegrityError:                      # database duplicate guard
        db.session.rollback()
        return False, "You already have a booking for this exam"

    return True, "Slot booked"


def cancel(student_id, booking_id):
    """Returns (True/False, message)."""
    booking = Booking.query.get(booking_id)
    if booking is None or booking.student_id != student_id:
        return False, "Booking not found"
    if booking.status != BookingStatus.Booked:
        return False, "Only active bookings can be cancelled"

    exam = Exam.query.get(booking.exam_id)
    if datetime.now() >= exam.booking_end:
        return False, "The cancellation deadline has passed"

    booking.status = BookingStatus.Cancelled
    (Slot.query.filter(Slot.id == booking.slot_id)
     .update({Slot.available_seats: Slot.available_seats + 1},
             synchronize_session=False))
    db.session.flush()

    slot = Slot.query.get(booking.slot_id)
    db.session.refresh(slot)
    if slot.status == SlotStatus.Full:
        slot.status = SlotStatus.Available
    _log(booking, "cancel", student_id, from_slot=slot.id)
    db.session.commit()
    return True, "Booking cancelled"
