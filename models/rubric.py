from sqlalchemy import CheckConstraint

from extensions import db


class rubrics_table(db.Model):
    __tablename__ = "rubrics"
    id = db.Column(db.Integer, autoincrement=True, unique=True, primary_key=True)
    exam_id = db.Column(db.Integer, forign_key=True)
    criterion_name = db.Column(db.String(100), nullable=True)
    max_marks = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(200))
    weightage = db.Column(db.Numeric(5, 2), nullable=False)
    __table_args__ = (
        CheckConstraint("max_marks > 0", name="check_rubric_marks"),
        CheckConstraint("weightage > 0 AND weightage <= 100", name="check_rubric_weightage"),
    )
