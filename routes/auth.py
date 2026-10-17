from flask import (Blueprint,
                   render_template, 
                   request, 
                   redirect,
                   url_for,
                   session,
                   flash,
                   abort
                   )
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user is None or not check_password_hash(user.password, password):
            flash("Wrong email or password")
            return redirect(url_for("auth.login"))
        
        session["user_id"] = user.id
        session["role"] = user.role.value
        session["name"] = user.name
        return redirect(url_for(user.role.value + ".dashboard"))

    return render_template("auth/login.html")

@auth_bp.route("/register/<role>", methods=["GET", "POST"])
def register(role):
    if role not in ("student", "examiner"):
        abort(404)

    if request.method == "POST":
        email = request.form["email"].strip().lower()

        if User.query.filter_by(email=email).first():
            flash("This email is already registered")
            return redirect(url_for("auth.register", role=role))

        user = User(
            name=request.form["name"].strip(),
            email=email,
            password=generate_password_hash(request.form["password"]),
            phone=request.form.get("phone"),
            role=role,
            status="active" if role == "student" else "pending",
        )

        if role == "student":
            user.enrollment_no = request.form.get("enrollment_no")
        else:
            user.department = request.form.get("department")

        db.session.add(user)
        db.session.commit()
        flash("Registered! Please login.")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", role=role)

@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("home"))