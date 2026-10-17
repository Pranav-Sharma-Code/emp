from sqlalchemy import UniqueConstraint

from extensions import db
from models.mixins import TimestampMixin


class ExamExaminer(TimestampMixin, db.Model):
    __tablename__ = "exam_examiners"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    __table_args__ = (
        UniqueConstraint("exam_id", "examiner_id", name="unique_exam_examiner"),
    )
