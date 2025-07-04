from e_commerce import db


class PromotionFlier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    image_filename = db.Column(db.String(200), nullable=False)
    
