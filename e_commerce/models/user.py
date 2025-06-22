from e_commerce import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    # Optional: profile fields
    date_joined = db.Column(db.DateTime, server_default=db.func.now())
    
    def __repr__(self):
        return f"<User {self.username}>"
