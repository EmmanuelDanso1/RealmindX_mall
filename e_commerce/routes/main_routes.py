from flask import Blueprint, render_template, request
from e_commerce.models import Product

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    products = Product.query.order_by(Product.date_created.desc()).all()
    return render_template('home.html', products=products)

@main_bp.route('/contact')
def contact():
    return render_template("contact.html")  # Replace with template if needed

@main_bp.route('/track-your-order', methods=['GET', 'POST'])
def track_order():
    if request.method == 'POST':
        order_id = request.form['order_id']
        billing_email = request.form['billing_email']
        # You could add logic here to fetch order data
        return render_template("track_order.html", order_id=order_id, billing_email=billing_email)
    return render_template("track_order.html")
