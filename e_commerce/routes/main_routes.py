from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from flask_mail import Mail,Message
import os
from e_commerce import db, mail
from e_commerce.models import Product, ProductRating, NewsletterSubscriber, Category, Order, OrderItem, InfoDocument
from e_commerce.utils.token import generate_verification_token, confirm_verification_token

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    page = request.args.get('page', 1, type=int)
    per_page = 12  # or any number you prefer

    products = Product.query.order_by(Product.date_created.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    return render_template('home.html', products=products)


@main_bp.route('/contact')
def contact():
    return render_template("contact.html")

@main_bp.route('/product/<int:product_id>')
def view_product(product_id):
    product = Product.query.get_or_404(product_id)
    user_rating = None
    if current_user.is_authenticated:
        user_rating = ProductRating.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    return render_template("product_detail.html", product=product, user_rating=user_rating)

@main_bp.route('/track-your-order', methods=['GET', 'POST'])
def track_order():
    order = None
    if request.method == 'POST':
        order_id = request.form['order_id']
        billing_email = request.form['billing_email']
        
        # Query the order by ID + email to verify
        order = Order.query.filter_by(id=order_id, email=billing_email).first()

        if not order:
            flash("No order found with that ID and email.", "warning")

    return render_template("track_order.html", order=order)

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
    query = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    in_stock = request.args.get('in_stock') == '1'
    page = request.args.get('page', 1, type=int)
    per_page = 6  # You can customize or make it dynamic

    # Base query with multi-field keyword search
    products_query = Product.query.filter(
        db.or_(
            Product.name.ilike(f"%{query}%"),
            Product.author.ilike(f"%{query}%"),
            Product.brand.ilike(f"%{query}%"),
            Product.subject.ilike(f"%{query}%"),
            Product.grade.ilike(f"%{query}"),
            Product.level.ilike(f"%{query}")
        )
    )

    # Apply optional filters
    if category_id:
        products_query = products_query.filter_by(category_id=category_id)
    if min_price is not None:
        products_query = products_query.filter(Product.price >= min_price)
    if max_price is not None:
        products_query = products_query.filter(Product.price <= max_price)
    if in_stock:
        products_query = products_query.filter_by(in_stock=True)

    # Pagination
    products = products_query.order_by(Product.date_created.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # Load categories for filtering UI
    categories = Category.query.order_by(Category.name).all()

    return render_template(
        'search_results.html',
        products=products,
        query=query,
        categories=categories
    )


# purchased order deleted
@main_bp.route('/delete-ordered-product/<int:product_id>', methods=['POST'])
@login_required
def delete_ordered_product(product_id):
    order_item = OrderItem.query.join(Order).filter(
        Order.user_id == current_user.id,
        OrderItem.product_id == product_id
    ).first()

    if not order_item:
        flash("Ordered product not found or unauthorized action.", "danger")
        return redirect(url_for('main.product_detail', product_id=product_id))

    try:
        db.session.delete(order_item)
        db.session.commit()
        flash("Product removed from your purchases.", "success")
    except Exception as e:
        db.session.rollback()
        print(f"Delete error: {e}")
        flash("An error occurred while deleting the product.", "danger")

    return redirect(url_for('main.product_detail', product_id=product_id))


#  order successful
@main_bp.route('/order-success/<int:order_id>')
@login_required
def order_success(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('order_success.html', order=order)


# autocomplete text
@main_bp.route('/autocomplete')
def autocomplete():
    term = request.args.get('term', '')
    results = Product.query.filter(Product.name.ilike(f"%{term}%")).limit(10).all()
    return jsonify([p.name for p in results])

# product rating
@main_bp.route('/product/<int:product_id>/rate', methods=['POST'])
@login_required
def rate_product(product_id):
    product = Product.query.get_or_404(product_id)

    # Check if the current user has purchased the product
    has_purchased = OrderItem.query.join(Order).filter(
        Order.user_id == current_user.id,
        OrderItem.product_id == product.id
    ).first()

    if not has_purchased:
        flash("You can only rate products you’ve purchased.", "warning")
        return redirect(url_for('main.product_detail', product_id=product.id))

    rating_value = int(request.form['rating'])

    # Check if the user has already rated
    existing_rating = ProductRating.query.filter_by(
        user_id=current_user.id, product_id=product.id
    ).first()

    if existing_rating:
        existing_rating.rating = rating_value
    else:
        new_rating = ProductRating(
            rating=rating_value,
            user_id=current_user.id,
            product_id=product.id
        )
        db.session.add(new_rating)

    db.session.commit()
    flash('Thanks for your rating!', 'success')
    return redirect(url_for('main.product_detail', product_id=product.id))


# rating
@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    user_rating = None
    if current_user.is_authenticated:
        user_rating = ProductRating.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    return render_template('product_detail.html', product=product, user_rating=user_rating)

# see ordered products
@main_bp.route('/my-products') 
@login_required
def purchased_products():
    purchased_items = (
        db.session.query(Product)
        .join(OrderItem)
        .join(Order)
        .filter(Order.user_id == current_user.id)
        .distinct()
        .all()
    )
    return render_template('my_products.html', products=purchased_items)

# contact
@main_bp.route('/submit', methods=['POST'])
def submit_contact():
    name = request.form['name']
    email = request.form['email']
    subject = request.form['subject']
    message_body = request.form['message']

    msg = Message(
        subject=f"Contact Form: {subject}",
        sender=email,
        recipients=[os.getenv('MAIL_USERNAME')]
    )

    msg.body = f"""
    You have received a new message from your website contact form:

    Name: {name}
    Email: {email}
    Subject: {subject}
    Message:
    {message_body}
    """

    try:
        mail.send(msg)
        flash("Your message has been sent to Realmindx successfully!", "success")
    except Exception as e:
        print(f"Mail sending failed: {e}")
        flash("An error occurred while sending your message. Please try again later.", "danger")

    return redirect(url_for('main.contact'))

# info
@main_bp.route('/info')
def info():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    source_filter = request.args.get('source', '').strip()

    query = InfoDocument.query

    # Apply search filter
    if search_query:
        query = query.filter(InfoDocument.title.ilike(f"%{search_query}%"))

    # Apply source filter
    if source_filter:
        query = query.filter(InfoDocument.source.ilike(f"%{source_filter}%"))

    # Paginate (6 per page)
    documents = query.order_by(InfoDocument.upload_date.desc()).paginate(page=page, per_page=9)

    return render_template(
        'info.html', 
        documents=documents,
        search_query=search_query,
        source_filter=source_filter
    )

