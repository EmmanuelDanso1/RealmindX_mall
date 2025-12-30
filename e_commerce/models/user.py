from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=True)
    # google auth
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    is_oauth_user = db.Column(db.Boolean, default=False)
    # Optional: profile fields
    date_joined = db.Column(db.DateTime, server_default=db.func.now())
    
    def __repr__(self):
        return f"<User {self.full_name}>"
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
        self.is_oauth_user = False
    
    def check_password(self, password):
        return check_password_hash(self.password, password)
