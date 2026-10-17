from extensions import db
from models.mixins import TimestampMixin


class Course(TimestampMixin, db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    status = db.Column(db.Boolean, nullable=False, default=True)  # True = active
