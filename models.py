from flask_sqlalchemy import SQLAlchemy;
db=SQLAlchemy()

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(100),unique=True,nullable=False)
    password=db.Column(db.String(200),nullable=False)

class MonthlyRecord(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    month = db.Column(db.String(20), nullable=False)   # e.g. "2025-06"
    income_sources = db.Column(db.Text)   # stored as JSON string
    expenses = db.Column(db.Text)         # stored as JSON string
    monthly_budget = db.Column(db.Float, default=0)
    savings_goal = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())