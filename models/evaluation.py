from sqlalchemy import CheckConstraint, UniqueConstraint

from extensions import db


class evaluations_table(db.Model):
    __tablename__ = "evaluations"
    id = db.Column(db.Integer, autoincrement=True, unique=True, primary_key=True)
    booking_id = db.Column(db.Integer, forign_key=True)
    total_marks = db.Column(db.Integer)
    remarks = db.Column(db.String(100))


class evaluation_scores_table(db.Model):
    __tablename__ = "evaluation_scores"
    id = db.Column(db.Integer, autoincrement=True, unique=True, primary_key=True)
    evaluation_id = db.Column(db.Integer, forign_key=True)
    rubrics_id = db.Column(db.Integer, forign_key=True)
    marks = db.Column(db.Integer)
    __table_args__ = (
        UniqueConstraint("evaluation_id", "rubrics_id", name="unique_evaluation_rubric"),
        CheckConstraint("marks >= 0", name="check_score_nonnegative"),
    )
