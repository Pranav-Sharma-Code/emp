from extensions import db
from models import Booking, BookingHistory, ExamExaminer, Slot, User
from models.enums import BookingStatus, SlotStatus, UserRole, UserStatus
from services.booking_service import _clashes


def _log(booking, action, admin_id, from_slot=None, to_slot=None, note=None):
    """One line in the booking history. Rows are never deleted."""
    db.session.add(BookingHistory(
        booking_id=booking.id, action=action, acted_by=admin_id,
        from_slot_id=from_slot, to_slot_id=to_slot, note=note,
    ))


def _fix_slot_status(slot_id):
    """Full <-> Available, depending on the seats left."""
    slot = Slot.query.get(slot_id)
    db.session.refresh(slot)
    if slot.status in (SlotStatus.Full, SlotStatus.Available):
        slot.status = SlotStatus.Full if slot.available_seats == 0 else SlotStatus.Available


def reschedule(booking_id, new_slot_id, admin_id):
    """Move a booking to another slot of the same exam. Returns (ok, message)."""
    booking = Booking.query.get(booking_id)
    if booking is None or booking.status != BookingStatus.Booked:
        return False, "Only active bookings can be rescheduled"

    new_slot = Slot.query.get(new_slot_id)
    if new_slot is None or new_slot.exam_id != booking.exam_id:
        return False, "Choose a slot of the same exam"
    if new_slot.id == booking.slot_id:
        return False, "The student is already in this slot"
    if new_slot.status in (SlotStatus.Cancelled, SlotStatus.Completed):
        return False, "That slot is not available"
    if _clashes(booking.student_id, new_slot, ignore_booking_id=booking.id):
        return False, "The student has another booking at that time"

    old_slot_id = booking.slot_id

    # take a seat in the new slot only if one is free
    taken = (Slot.query
             .filter(Slot.id == new_slot.id, Slot.available_seats > 0)
             .update({Slot.available_seats: Slot.available_seats - 1},
                     synchronize_session=False))
    if taken == 0:
        db.session.rollback()
        return False, "The new slot is full"

    # give the seat back in the old slot
    (Slot.query.filter(Slot.id == old_slot_id)
     .update({Slot.available_seats: Slot.available_seats + 1},
             synchronize_session=False))

    booking.slot_id = new_slot.id
    booking.old_slot_id = old_slot_id
    db.session.flush()
    _fix_slot_status(new_slot.id)
    _fix_slot_status(old_slot_id)
    _log(booking, "reschedule", admin_id, from_slot=old_slot_id, to_slot=new_slot.id)
    db.session.commit()
    return True, "Booking moved to the new slot"


def cancel_booking(booking_id, admin_id):
    """Admin cancels a booking (no deadline for the Admin)."""
    booking = Booking.query.get(booking_id)
    if booking is None or booking.status != BookingStatus.Booked:
        return False, "Only active bookings can be cancelled"

    booking.status = BookingStatus.Cancelled
    (Slot.query.filter(Slot.id == booking.slot_id)
     .update({Slot.available_seats: Slot.available_seats + 1},
             synchronize_session=False))
    db.session.flush()
    _fix_slot_status(booking.slot_id)
    _log(booking, "cancel", admin_id, from_slot=booking.slot_id, note="cancelled by admin")
    db.session.commit()
    return True, "Booking cancelled"


def change_examiner(slot_id, examiner_id, admin_id):
    """Give a slot to another approved examiner. Returns (ok, message)."""
    slot = Slot.query.get(slot_id)
    if slot is None or slot.status in (SlotStatus.Cancelled, SlotStatus.Completed):
        return False, "This slot cannot be changed"

    new = User.query.get(examiner_id)
    if new is None or new.role != UserRole.Examiner or new.status != UserStatus.Active:
        return False, "Choose an approved examiner"
    if new.id == slot.examiner_id:
        return False, "That examiner already owns this slot"

    clash = (Slot.query
             .filter(Slot.examiner_id == new.id, Slot.id != slot.id,
                     Slot.slot_date == slot.slot_date,
                     Slot.status != SlotStatus.Cancelled,
                     Slot.start_time < slot.end_time,
                     Slot.end_time > slot.start_time)
             .first())
    if clash:
        return False, "%s already has a slot at that time" % new.name

    old = User.query.get(slot.examiner_id)
    slot.examiner_id = new.id

    # the new examiner must be assigned to the exam
    if not ExamExaminer.query.filter_by(exam_id=slot.exam_id, examiner_id=new.id).first():
        db.session.add(ExamExaminer(exam_id=slot.exam_id, examiner_id=new.id,
                                    assigned_by=admin_id))
    db.session.flush()

    note = ("examiner %s -> %s" % (old.name, new.name))[:200]
    for b in Booking.query.filter(Booking.slot_id == slot.id,
                                  Booking.status != BookingStatus.Cancelled):
        _log(b, "examiner_change", admin_id, from_slot=slot.id, to_slot=slot.id, note=note)

    db.session.commit()
    return True, "Slot now belongs to " + new.name
