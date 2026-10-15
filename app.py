from flask import Flask, render_template

from extensions import db


def create_app():
    app = Flask(__name__)
    app.config["SQLAlchemy_DATABASE_URI"] = "sqlite:///app.db"

    db.init_app(app)

    import models  # registers all tables

    @app.route("/")
    def home():
        return render_template("home.html")

    return app


app = create_app()
