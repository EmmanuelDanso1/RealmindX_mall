from extensions import db
from datetime import datetime

class NewsletterSubscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    subscribed_on = db.Column(db.DateTime, default=datetime.utcnow)
