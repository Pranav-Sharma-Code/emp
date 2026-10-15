from extensions import db

class courses_table(db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, autoincrement=True, unique=True, primary_key=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    status = db.Column(db.Boolen, nullable=False, default=True)
