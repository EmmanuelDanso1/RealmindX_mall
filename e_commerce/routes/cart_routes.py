# Flask routes for cart functionality
from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from flask_login import login_required, current_user
import requests
from e_commerce.models import Product, Order, OrderItem
from e_commerce import db, mail
from flask_mail import Message
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
    cart = session.get('cart', {})

    product_id_str = str(product.id)

    if product_id_str in cart:
        cart[product_id_str]['quantity'] += 1
    else:
        cart[product_id_str] = {
            'name': product.name,
            'price': float(product.discounted_price if product.discount_percentage > 0 else product.price),
            'image': product.image_filename,
            'quantity': 1
        }

    session['cart'] = cart  # <- This ensures session gets updated
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

# check out
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
            price_to_use = product.discounted_price if product.discount_percentage > 0 else product.price
            total = price_to_use * quantity
            grand_total += total

            items.append({
                'product_id': product.id,
                'original_price': product.price,
                'product_name': product.name,
                'price': price_to_use,
                'quantity': quantity,
                'total': total
            })

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
                "amount": int(grand_total * 100),
                "metadata": {
                    "full_name": full_name,
                    "address": address,
                    "user_id": current_user.id,
                    "cart": items
                },
                "callback_url": url_for('cart.payment_callback', _external=True)
            }

            try:
                response = requests.post(
                    'https://api.paystack.co/transaction/initialize',
                    json=data,
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()
                payment_url = response.json()['data']['authorization_url']
                session['paid_cart_items'] = items
                return redirect(payment_url)

            except requests.exceptions.Timeout:
                flash("Request timed out. Please try again.", "warning")
                return render_template("errors/timeout.html"), 504
            except requests.exceptions.ConnectionError:
                flash("Could not connect to Paystack. Check your internet and try again.", "danger")
                return render_template("errors/connection_error.html"), 502
            except requests.exceptions.RequestException as e:
                flash("Something went wrong while initializing payment.", "danger")
                return render_template("errors/general_error.html", error=str(e)), 500

        elif payment_method == 'cod':
            order = Order(
                user_id=current_user.id,
                full_name=full_name,
                email=email,
                address=address,
                total_amount=grand_total,
                payment_method='cash on delivery',
                status='pending'
            )
            db.session.add(order)
            db.session.flush()

            order_items_data = []
            for item in items:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item['product_id'],
                    quantity=int(item['quantity']),
                    price=float(item['price'])
                )
                db.session.add(order_item)
                order_items_data.append({
                    'product_id': item['product_id'],
                    'product_name': item['product_name'],
                    'quantity': int(item['quantity']),
                    'price': float(item['price'])
                })

            db.session.commit()

            try:
                api_data = {
                    'order_id': order.id,
                    'user_id': current_user.id,
                    'full_name': full_name,
                    'email': email,
                    'address': address,
                    'total_amount': grand_total,
                    'payment_method': 'cod',
                    'items': order_items_data
                }
                api_headers = {
                    'Authorization': f'Bearer {os.getenv("API_TOKEN")}',
                    'Content-Type': 'application/json'
                }
                api_res = requests.post(
                    'http://127.0.0.1:5000/api/orders',
                    json=api_data,
                    headers=api_headers,
                    timeout=10
                )
                if api_res.status_code == 201:
                    flash("Order successful.", "success")
                else:
                    flash(f"Order placed, but failed to sync to admin dashboard. {api_res.status_code}: {api_res.text}", "warning")
            except Exception as e:
                flash(f"Order placed, but error syncing to admin dashboard: {e}", "warning")

            flash(f"Order placed successfully. Your Order ID is {order.id}. You will pay on delivery.", "success")
            session.pop('cart', None)
            return redirect(url_for('main.order_success', order_id=order.id))

    return render_template('checkout.html', cart=items, total=grand_total)


@cart_bp.route('/payment/callback')
@login_required
def payment_callback():
    reference = request.args.get('reference')
    if not reference:
        flash("Missing payment reference.", "danger")
        return redirect(url_for('main.home'))

    headers = {'Authorization': f'Bearer {os.getenv("PAYSTACK_SECRET_KEY")}'}
    verify_url = f'https://api.paystack.co/transaction/verify/{reference}'

    try:
        response = requests.get(verify_url, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
    except requests.RequestException:
        flash("Failed to verify payment. Please try again.", "danger")
        return redirect(url_for('cart.view_cart'))

    if result['status'] and result['data']['status'] == 'success':
        data = result['data']
        metadata = data['metadata']
        cart_items = metadata.get('cart', [])

        order = Order(
            user_id=metadata.get('user_id'),
            full_name=metadata['full_name'],
            email=data['customer']['email'],
            address=metadata['address'],
            total_amount=data['amount'] / 100,
            payment_method='paystack',
            status='paid'
        )
        db.session.add(order)
        db.session.flush()

        for item in cart_items:
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=item['product_id'],
                quantity=int(item['quantity']),
                price=float(item['price'])  # discounted price used
            ))

        db.session.commit()

        # Sync to admin dashboard
        try:
            api_data = {
                'order_id': order.id,
                'user_id': order.user_id,
                'full_name': order.full_name,
                'email': order.email,
                'address': order.address,
                'total_amount': order.total_amount,
                'payment_method': order.payment_method,
                'items': cart_items
            }
            api_headers = {
                'Authorization': f'Bearer {os.getenv("API_TOKEN")}',
                'Content-Type': 'application/json'
            }
            api_res = requests.post(
                'http://127.0.0.1:5000/api/orders',
                json=api_data,
                headers=api_headers,
                timeout=10
            )
            if api_res.status_code == 201:
                flash("Order synced to admin dashboard.", "success")
            else:
                flash("Order placed, but sync failed.", "warning")
        except Exception as e:
            flash(f"Sync error: {e}", "warning")

        session.pop('cart', None)
        session.pop('paid_cart_items', None)

        return render_template("order_success.html", order=order)

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

# Add quantity of products to be purchased
@cart_bp.route('/add/<int:product_id>', methods=['GET', 'POST'])
def add_quantity(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        quantity = int(request.form.get('quantity', 1))

        cart = session.get('cart', {})
        product_id_str = str(product.id)

        if product_id_str in cart:
            cart[product_id_str]['quantity'] += quantity
        else:
            cart[product_id_str] = {
                'product_id': product.id,
                'name': product.name,
                'price': float(product.discounted_price if product.discount_percentage > 0 else product.price),
                'quantity': quantity
            }

        session['cart'] = cart
        session.modified = True

        flash('Item added to cart successfully.', 'success')
        return redirect(url_for('cart.view_cart'))

    return render_template('cart/add_quantity.html', product=product)
