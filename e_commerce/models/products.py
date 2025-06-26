from datetime import datetime
from e_commerce import db

class Product(db.Model):
    __tablename__ = 'product'  # Optional, but makes FK references safer

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_filename = db.Column(db.String(120))
    in_stock = db.Column(db.Boolean, default=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    # Ratings relationship
    ratings = db.relationship('ProductRating', back_populates='product', lazy=True)

    # Category relationship
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category', back_populates='products')
    
    # Order relationship
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    # Average rating property
    @property
    def average_rating(self):
        if not self.ratings:
            return 0
        return round(sum(r.rating for r in self.ratings) / len(self.ratings), 1)
