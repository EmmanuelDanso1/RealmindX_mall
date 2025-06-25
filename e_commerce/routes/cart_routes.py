# Flask routes for cart functionality
from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from flask_login import login_required, current_user
import requests
from e_commerce.models import Product, Order, OrderItem
from e_commerce import db
from datetime import datetime
import os

cart_bp = Blueprint('cart', __name__)

# Utility: initialize cart if not in session
def get_cart():
    if 'cart' not in session:
        session['cart'] = {}
    return session['cart']

# Add to cart
@cart_bp.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    cart = get_cart()

    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] += 1
    else:
        cart[str(product_id)] = {
            'name': product.name,
            'price': product.price,
            'image': product.image_filename,
            'quantity': 1
        }

    session.modified = True
    flash(f"Added {product.name} to cart.", "success")
    return redirect(request.referrer or url_for('main.home'))

# View Cart
@cart_bp.route('/cart')
def view_cart():
    cart = get_cart()
    items = []
    total = 0

    for product_id, item in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            quantity = item['quantity']
            total += product.price * quantity
            items.append({'product': product, 'quantity': quantity})

    return render_template('cart.html', cart=items, total=total)

# Remove item from cart
@cart_bp.route('/cart/remove/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    session.modified = True
    flash("Item removed from cart.", "info")
    return redirect(url_for('cart.view_cart'))

# Checkout
@cart_bp.route('/cart/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('main.home'))

    items = []
    grand_total = 0

    for product_id, item in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            quantity = item['quantity']
            total = product.price * quantity
            grand_total += total
            items.append({'product': product, 'quantity': quantity, 'total': total})

    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        address = request.form['address']
        payment_method = request.form['payment_method']

        if payment_method == 'paystack':
            headers = {
                'Authorization': f'Bearer {os.getenv("PAYSTACK_SECRET_KEY")}',
                'Content-Type': 'application/json',
            }

            data = {
                "email": email,
                "amount": int(grand_total * 100),  # Convert to kobo
                "metadata": {
                    "full_name": full_name,
                    "address": address,
                    "user_id": current_user.id,
                    "cart": [
                        {
                            "product_id": p['product'].id,
                            "product_name": p['product'].name,
                            "quantity": p['quantity'],
                            "price": p['product'].price
                        } for p in items
                    ]
                },
                "callback_url": url_for('cart.payment_callback', _external=True)
            }

            response = requests.post('https://api.paystack.co/transaction/initialize', headers=headers, json=data)

            if response.status_code == 200:
                auth_url = response.json()['data']['authorization_url']
                return redirect(auth_url)
            else:
                flash("Failed to initiate Paystack payment.", "danger")
                return redirect(url_for('cart.checkout'))

        elif payment_method == 'cod':
            # You can store the order to DB immediately here
            flash("Order placed. You will pay on delivery.", "success")
            session.pop('cart', None)
            return redirect(url_for('main.order_success'))

    return render_template('checkout.html', cart=items, total=grand_total)

# payment callback
@cart_bp.route('/payment/callback')
@login_required
def payment_callback():
    reference = request.args.get('reference')
    if not reference:
        flash("Missing payment reference.", "danger")
        return redirect(url_for('main.home'))

    headers = {
        'Authorization': f'Bearer {os.getenv("PAYSTACK_SECRET_KEY")}'
    }

    verify_url = f'https://api.paystack.co/transaction/verify/{reference}'
    response = requests.get(verify_url, headers=headers)
    result = response.json()

    if result['status'] and result['data']['status'] == 'success':
        metadata = result['data']['metadata']
        full_name = metadata['full_name']
        email = result['data']['customer']['email']
        address = metadata['address']
        user_id = metadata.get('user_id')

        # Fetch cart data from session
        cart_items = session.get('paid_cart_items', [])

        # Fix here: item is a dict, not an object
        grand_total = sum(item['product'].price * item['quantity'] for item in cart_items)

        # Save Order
        order = Order(
            user_id=user_id,
            full_name=full_name,
            email=email,
            address=address,
            total_amount=grand_total,
            payment_method='paystack',
            status='paid'
        )
        db.session.add(order)
        db.session.commit()

        # Save each item
        for item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item['product'].id,
                quantity=item['quantity'],
                price=item['product'].price
            )
            db.session.add(order_item)

        db.session.commit()

        # Clear cart
        session.pop('cart', None)
        session.pop('paid_cart_items', None)

        flash("Payment successful and order placed!", "success")
        return redirect(url_for('main.order_success'))

    else:
        flash("Payment verification failed.", "danger")
        return redirect(url_for('cart.view_cart'))


def get_cart_items_for_user(user_id=None):
    cart = session.get('cart', {})
    items = []

    for product_id_str, data in cart.items():
        product_id = int(product_id_str)
        product = Product.query.get(product_id)

        if product:
            items.append({
                'product': product,
                'quantity': data['quantity']
            })

    return items
