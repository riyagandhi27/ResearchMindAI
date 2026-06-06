from datetime import datetime
from extensions import db


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)

    filename = db.Column(db.String(255), nullable=False)

    filetype = db.Column(db.String(50), nullable=False)

    source = db.Column(db.String(50), nullable=True)   # ✅ FIXED

    content = db.Column(db.Text, nullable=False)

    upload_date = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class ChatHistory(db.Model):
    __tablename__ = "chat_history"

    id = db.Column(db.Integer, primary_key=True)

    question = db.Column(db.Text, nullable=False)

    answer = db.Column(db.Text, nullable=False)

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )