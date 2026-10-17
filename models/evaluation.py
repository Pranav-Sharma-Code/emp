from sqlalchemy import CheckConstraint, UniqueConstraint

from extensions import db
from models.enums import EvaluationStatus, sa_enum
from models.mixins import TimestampMixin


class Evaluation(TimestampMixin, db.Model):
    __tablename__ = "evaluations"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), unique=True, nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(sa_enum(EvaluationStatus), nullable=False, default=EvaluationStatus.Draft)
    total_marks = db.Column(db.Numeric(6, 2))
    remarks = db.Column(db.String(500))


class EvaluationScore(TimestampMixin, db.Model):
    __tablename__ = "evaluation_scores"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey("evaluations.id"), nullable=False)
    rubric_id = db.Column(db.Integer, db.ForeignKey("rubrics.id"), nullable=False)
    marks = db.Column(db.Numeric(6, 2), nullable=False)
    __table_args__ = (
        UniqueConstraint("evaluation_id", "rubric_id", name="unique_evaluation_rubric"),
        CheckConstraint("marks >= 0", name="check_score_nonnegative"),
    )
