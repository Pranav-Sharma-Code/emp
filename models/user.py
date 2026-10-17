from extensions import db
from models.enums import UserRole, UserStatus, sa_enum
from models.mixins import TimestampMixin


class User(TimestampMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(sa_enum(UserRole), nullable=False, default=UserRole.Student)
    status = db.Column(sa_enum(UserStatus), nullable=False, default=UserStatus.Pending)
    phone = db.Column(db.String(20))
    department = db.Column(db.String(100))
    enrollment_no = db.Column(db.String(30), unique=True)
