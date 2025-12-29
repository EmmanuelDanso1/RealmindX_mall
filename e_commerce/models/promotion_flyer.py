from extensions import db
from datetime import datetime

class PromotionFlier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    image_filename = db.Column(db.String(200), nullable=False)
    external_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
