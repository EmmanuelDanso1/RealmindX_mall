from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from e_commerce import db
from e_commerce.models import Product, ProductRating, NewsletterSubscriber

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    products = Product.query.order_by(Product.date_created.desc()).all()
    return render_template('home.html', products=products)

@main_bp.route('/contact')
def contact():
    return render_template("contact.html")

# Product rating
@main_bp.route('/rate/<int:product_id>', methods=['POST'])
@login_required
def rate_product(product_id):
    rating_value = int(request.form['rating'])
    existing = ProductRating.query.filter_by(user_id=current_user.id, product_id=product_id).first()

    if existing:
        existing.rating = rating_value
    else:
        new_rating = ProductRating(user_id=current_user.id, product_id=product_id, rating=rating_value)
        db.session.add(new_rating)

    db.session.commit()
    flash("Rating submitted!", "success")
    return redirect(url_for('main.home'))

@main_bp.route('/product/<int:product_id>')
def view_product(product_id):
    product = Product.query.get_or_404(product_id)
    user_rating = None
    if current_user.is_authenticated:
        user_rating = ProductRating.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    return render_template("product_detail.html", product=product, user_rating=user_rating)

@main_bp.route('/track-your-order', methods=['GET', 'POST'])
def track_order():
    if request.method == 'POST':
        order_id = request.form['order_id']
        billing_email = request.form['billing_email']
        # You could add logic here to fetch order data
        return render_template("track_order.html", order_id=order_id, billing_email=billing_email)
    return render_template("track_order.html")

# NewsLetter subscription
@main_bp.route('/subscribe-newsletter', methods=['POST'])
def subscribe_newsletter():
    email = request.form.get('email')

    if not email:
        flash("Please enter a valid email address.", "warning")
        return redirect(request.referrer or url_for('main.home'))

    # Check if already subscribed
    existing = NewsletterSubscriber.query.filter_by(email=email).first()
    if existing:
        flash("You're already subscribed!", "info")
    else:
        new_subscriber = NewsletterSubscriber(email=email)
        db.session.add(new_subscriber)
        db.session.commit()
        flash("Thanks for subscribing to our newsletter!", "success")

    return redirect(request.referrer or url_for('main.home'))
