from e_commerce import db

class ProductRating(db.Model):
    __tablename__ = 'product_rating'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # e.g., 1 to 5

    # ✅ Back-reference to Product
    product = db.relationship('Product', back_populates='ratings')

    # ✅ Optional: Backref to User (assumes you have a User model)
    user = db.relationship('User', backref='ratings')
