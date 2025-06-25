from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from flask_mail import Mail,Message
from e_commerce import db, mail
from e_commerce.models import Product, ProductRating, NewsletterSubscriber, Category
from e_commerce.utils.token import generate_verification_token, confirm_verification_token

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
@main_bp.route('/subscribe', methods=['POST'])
def subscribe_newsletter():
    email = request.form.get('email')

    existing = NewsletterSubscriber.query.filter_by(email=email).first()
    if existing:
        flash("Email is already subscribed.", "info")
        return redirect(url_for('main.home'))

    token = generate_verification_token(email)
    confirm_url = url_for('main.confirm_subscription', token=token, _external=True)
    html = render_template('emails/confirm_newsletter.html', confirm_url=confirm_url)

    msg = Message("Confirm your newsletter subscription", recipients=[email], html=html)
    mail.send(msg)

    new_subscriber = NewsletterSubscriber(email=email, is_verified=False)
    db.session.add(new_subscriber)
    db.session.commit()

    flash("A confirmation email has been sent to verify your subscription.", "success")
    return redirect(url_for('main.home'))

@main_bp.route('/confirm-newsletter/<token>')
def confirm_subscription(token):
    email = confirm_verification_token(token)
    if not email:
        flash("The confirmation link is invalid or has expired.", "danger")
        return redirect(url_for('main.home'))

    subscriber = NewsletterSubscriber.query.filter_by(email=email).first()
    if not subscriber:
        flash("No matching subscriber found.", "warning")
        return redirect(url_for('main.home'))

    if subscriber.is_verified:
        flash("Subscription already confirmed.", "info")
    else:
        subscriber.is_verified = True
        db.session.commit()
        flash("Your subscription has been confirmed. Thank you!", "success")

    return redirect(url_for('main.home'))

# search for product
@main_bp.route('/search')
def search():
    query = request.args.get('q', '')
    category_id = request.args.get('category', type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    in_stock = request.args.get('in_stock') == '1'

    products = Product.query.filter(Product.name.ilike(f'%{query}%'))

    # ✅ Filter by category
    if category_id:
        products = products.filter_by(category_id=category_id)

    if min_price is not None:
        products = products.filter(Product.price >= min_price)
    if max_price is not None:
        products = products.filter(Product.price <= max_price)
    if in_stock:
        products = products.filter_by(in_stock=True)

    categories = Category.query.order_by(Category.name).all()

    return render_template(
        'search_results.html',
        products=products.all(),
        query=query,
        categories=categories
    )

# autocomplete text
@main_bp.route('/autocomplete')
def autocomplete():
    term = request.args.get('term', '')
    results = Product.query.filter(Product.name.ilike(f"%{term}%")).limit(10).all()
    return jsonify([p.name for p in results])
