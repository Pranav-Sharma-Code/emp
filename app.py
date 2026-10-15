from flask import Flask, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import date, time
import enum

app = Flask(__name__)
app.config["SQLAlchemy_DATABASE_URI"] = "sqlite:///app.db"

db = SQLAlchemy(app)

class UserRole(enum.Enum):
    Admin = "admin"
    Student = "Student"
    Examiner = "Examiner"

class status(enum.Enum):
    

class user_table(db.Model):
    id = db.Column(db.Integer, unique=True, autoincrement=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, primary_key=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.Student)


class student_table(db.Model):
    id = db.Column(db.Integer, autoincrement=True, unique=True)
    email = db.Column(db.String(120), nullable=False, primary_key=True, unique=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer)
    exam_id = db.Column(db.Integer)


class Examiner_table(db.Model):
    id = db.Column(db.Integer, autoincrement=True, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    exam_id = db.Column(db.Integer)

class exam_table(db.Model):
    id = db.Column(db.Integer, autoincrement=True, unique=True, primary_key=True)
    slot = db.Column(db.time, unique=True, nullable=False)
    date = db.Column(db.date, nullable=False)
    Examiner = db.Column(db.String(100), nullable=False)

class course_table(db.Model):
    id = db.Column(db.Integer, autoincrement=True, unique=True, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    exam_id = db.Column(db.

@app.route('/')
def home():
    return render_template("home.html")