from decimal import Decimal, InvalidOperation

from extensions import db
from models import (Booking, BookingHistory, Evaluation, EvaluationScore,
                    Exam, Rubric, Slot)
from models.enums import BookingStatus, EvaluationStatus, ExamState


def calculate_total(rubrics, marks, exam_max):
    """sum(awarded / criterion max * weightage) / 100 * exam max marks"""
    percent = sum((marks[r.id] / r.max_marks * r.weightage for r in rubrics),
                  Decimal(0))
    return (percent / 100 * exam_max).quantize(Decimal("0.01"))


def submit(examiner_id, booking_id, raw_marks, remarks):
    """raw_marks = {rubric_id: text typed by the examiner}. Returns (ok, message)."""
    booking = Booking.query.get(booking_id)
    if booking is None or booking.status == BookingStatus.Cancelled:
        return False, "Booking not found"

    slot = Slot.query.get(booking.slot_id)
    if slot.examiner_id != examiner_id:
        return False, "You can only evaluate your own students"

    exam = Exam.query.get(booking.exam_id)
    if exam.status != ExamState.Closed or exam.results_published:
        return False, "This exam cannot be evaluated right now"

    rubrics = Rubric.query.filter_by(exam_id=exam.id).all()
    marks = {}
    for r in rubrics:
        try:
            value = Decimal(str(raw_marks.get(r.id, "")).strip())
        except InvalidOperation:
            return False, "Enter marks for " + r.criterion_name
        if not value.is_finite() or value < 0 or value > r.max_marks:
            return False, "%s: marks must be between 0 and %s" % (r.criterion_name, r.max_marks)
        marks[r.id] = value

    evaluation = Evaluation.query.filter_by(booking_id=booking.id).first()
    if evaluation is None:
        evaluation = Evaluation(booking_id=booking.id, examiner_id=examiner_id)
        db.session.add(evaluation)
        db.session.flush()

    evaluation.remarks = remarks.strip()
    evaluation.total_marks = calculate_total(rubrics, marks, exam.max_marks)
    evaluation.status = EvaluationStatus.Submitted

    old = {s.rubric_id: s for s in
           EvaluationScore.query.filter_by(evaluation_id=evaluation.id)}
    for r in rubrics:
        if r.id in old:
            old[r.id].marks = marks[r.id]
        else:
            db.session.add(EvaluationScore(evaluation_id=evaluation.id,
                                           rubric_id=r.id, marks=marks[r.id]))

    if booking.status == BookingStatus.Booked:
        booking.status = BookingStatus.Completed
        db.session.add(BookingHistory(booking_id=booking.id, action="completed",
                                      acted_by=examiner_id))
    db.session.commit()
    return True, "Evaluation saved"
