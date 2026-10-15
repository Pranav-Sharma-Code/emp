from flask import Flask, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import date, time

app = Flask(__name__)
app.config["SQLAlchemy_DATABASE_URI"] = "sqlite:///app.db"

db = SQLAlchemy(app)

class student_table(db.Model):
    id = db.Column(db.Integer, autoincrement=True, unique=True)
    email = db.Column(db.String(120), nullabl=False, primary_key=True, unique=True)
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
    exam_id = db.Column(db.Integer)

@app.route('/')
def home():
    return render_template("home.html")