from flask import Flask, render_template
from werkzeug.security import generate_password_hash

from extensions import db
import models
from models import User

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-later"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"

db.init_app(app)

from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.examiner import examiner_bp
from routes.student import student_bp
import routes.admin_exam
import routes.admin_extra

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(examiner_bp)
app.register_blueprint(student_bp)

@app.route("/")
def home():
    return render_template("home.html")

with app.app_context():
    db.create_all()

    if not User.query.filter_by(role="admin").first():
        admin = User(
            name="Admin",
            email="admin@emp.com",
            password=generate_password_hash("admin123"),
            role="admin",
            status="active",
        )

        db.session.add(admin)
        db.session.commit()


if __name__ == "__main__":
    app.run(debug=True)