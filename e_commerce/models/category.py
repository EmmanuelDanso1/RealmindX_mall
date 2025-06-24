from e_commerce import db 

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    # One-to-many relationship with Product
    products = db.relationship('Product', back_populates='category', lazy=True)
