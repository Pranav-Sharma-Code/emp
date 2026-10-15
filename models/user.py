from extensions import db
from models.enums import UserRole, UserStatus


class user_table(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, unique=True, autoincrement=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, primary_key=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.Student)
    status = db.Column(db.Enum(UserStatus), nullable=False, default=UserStatus.Pending)
    phone = db.Column(db.String(20), nullable=True)
    departemnt = db.Column(db.String(100), nullable=True)
    enrollment_no = db.Column(db.Integer, unique=True, nullable=True)
