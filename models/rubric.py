from sqlalchemy import CheckConstraint

from extensions import db
from models.mixins import TimestampMixin


class Rubric(TimestampMixin, db.Model):
    __tablename__ = "rubrics"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    criterion_name = db.Column(db.String(100), nullable=False)
    max_marks = db.Column(db.Integer, nullable=False)
    weightage = db.Column(db.Numeric(5, 2), nullable=False)
    description = db.Column(db.String(200))
    __table_args__ = (
        CheckConstraint("max_marks > 0", name="check_rubric_marks"),
        CheckConstraint("weightage > 0 AND weightage <= 100", name="check_rubric_weightage"),
    )
