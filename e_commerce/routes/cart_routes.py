# Flask routes for cart functionality
from flask import Blueprint, render_template, redirect, url_for, flash, session, request, current_app
from flask_login import login_required, current_user
import requests
from e_commerce.utils.helpers import get_random_unique_order_id
from e_commerce.models import Product, Order, OrderItem
from extensions import db, mail
from flask_mail import Message
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

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


# Getting random ids for order
def send_order_email(to, full_name, order_id, items, total, payment_method, address, phone, order_date, subtotal, discount):
    try:
        msg = Message(
            subject=f"Order Confirmation - Order #{order_id}",
            recipients=[to],
            sender=os.getenv('MAIL_USERNAME')
        )
        msg.html = render_template(
            'emails/order_confirmation.html',
            full_name=full_name,
            order_id=order_id,
            items=items,
            total=total,
            payment_method=payment_method,
            address=address,
            phone=phone,
            order_date=order_date,
            subtotal=subtotal,
            discount=discount
        )
        mail.send(msg)
    except Exception as e:
        print(f"Email sending failed: {e}")


@cart_bp.route('/cart/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('main.home'))

    items = []
    grand_total = 0
    discount = 0
    subtotal = 0

    for product_id, item in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            price = product.price
            quantity = item['quantity']
            discounted_price = product.discounted_price if product.discount_percentage > 0 else product.price
            total = discounted_price * quantity
            grand_total += total
            subtotal += price * quantity
            discount += (price - discounted_price) * quantity

            items.append({
                'product_id': product.id,
                'original_price': product.price,
                'product_name': product.name,
                'price': discounted_price,
                'quantity': quantity,
                'total': total
            })

    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        address = request.form['address']
        payment_method = request.form['payment_method']
        phone = request.form.get('phone', '')

        unique_order_id = get_random_unique_order_id()
        
        current_app.logger.info(
            f"[Bookshop] Checkout initiated by user {current_user.id} - Order ID: {unique_order_id}"
        )

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
                    "order_id": unique_order_id,
                    "address": address,
                    "user_id": current_user.id,
                    "cart": items,
                    "phone": phone
                },
                "callback_url": url_for('cart.payment_callback', _external=True)
            }

            try:
                current_app.logger.info(f"[Bookshop] Initializing Paystack payment for order {unique_order_id}")
                response = requests.post(
                    'https://api.paystack.co/transaction/initialize',
                    json=data,
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()
                payment_url = response.json()['data']['authorization_url']
                session['paid_cart_items'] = items
                session['pending_order_id'] = unique_order_id
                session['pending_order_meta'] = {
                    'full_name': full_name,
                    'email': email,
                    'address': address,
                    'total': grand_total,
                    'phone': phone,
                    'subtotal': subtotal,
                    'discount': discount
                }
                current_app.logger.info(f"[Bookshop] Paystack payment initialized for {unique_order_id}")
                return redirect(payment_url)

            except requests.exceptions.Timeout:
                current_app.logger.error(f"[Bookshop] Paystack timeout for order {unique_order_id}")
                flash("Request timed out. Please try again.", "warning")
                return render_template("errors/timeout.html"), 504
            except requests.exceptions.ConnectionError:
                current_app.logger.error(f"[Bookshop] Paystack connection error for order {unique_order_id}")
                flash("Could not connect to Paystack. Check your internet and try again.", "danger")
                return render_template("errors/connection_error.html"), 502
            except requests.exceptions.RequestException as e:
                current_app.logger.exception(f"[Bookshop] Paystack error for order {unique_order_id}: {e}")
                flash("Something went wrong while initializing payment.", "danger")
                return render_template("errors/general_error.html", error=str(e)), 500

        elif payment_method == 'cod':
            current_app.logger.info(f"[Bookshop] Processing COD order {unique_order_id}")
            
            order = Order(
                user_id=current_user.id,
                order_id=unique_order_id,
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
            current_app.logger.info(f"[Bookshop] Order {unique_order_id} saved locally")

            # Send confirmation email
            try:
                send_order_email(
                    to=email,
                    full_name=full_name,
                    order_id=unique_order_id,
                    items=order_items_data,
                    total=grand_total,
                    payment_method="Cash on Delivery",
                    address=address,
                    phone=phone,
                    order_date=datetime.now().strftime('%d %B %Y %I:%M:%S%p').lower(),
                    subtotal=subtotal,
                    discount=discount
                )
                current_app.logger.info(f"[Bookshop] Confirmation email sent for order {unique_order_id}")
            except Exception as e:
                current_app.logger.error(f"[Bookshop] Failed to send email for order {unique_order_id}: {e}")

            # Sync to Learning Platform Admin Dashboard
            try:
                api_base_url = os.getenv('API_BASE_URL')
                api_token = os.getenv('API_TOKEN')
                
                if not api_base_url or not api_token:
                    current_app.logger.error("[Bookshop] Missing API_BASE_URL or API_TOKEN in environment")
                    flash("Order placed locally but could not sync to admin dashboard (missing config).", "warning")
                else:
                    api_data = {
                        'order_id': unique_order_id,
                        'user_id': current_user.id,
                        'full_name': full_name,
                        'email': email,
                        'address': address,
                        'phone': phone,
                        'total_amount': grand_total,
                        'payment_method': 'cod',
                        'items': order_items_data
                    }
                    api_headers = {
                        'Authorization': f'Bearer {api_token}',
                        'Content-Type': 'application/json'
                    }
                    
                    current_app.logger.info(
                        f"[Bookshop] Syncing order {unique_order_id} to admin dashboard at {api_base_url}"
                    )
                    
                    api_res = requests.post(
                        f'{api_base_url}/orders',
                        json=api_data,
                        headers=api_headers,
                        timeout=10
                    )
                    
                    if api_res.status_code == 201:
                        current_app.logger.info(
                            f"[Bookshop] ✓ Order {unique_order_id} synced successfully to admin dashboard"
                        )
                    else:
                        current_app.logger.error(
                            f"[Bookshop] Failed to sync order {unique_order_id}: "
                            f"Status {api_res.status_code}, Response: {api_res.text}"
                        )
                        flash(
                            f"Order placed, but failed to sync to admin dashboard. "
                            f"Status: {api_res.status_code}", 
                            "warning"
                        )
                        
            except requests.exceptions.Timeout:
                current_app.logger.error(
                    f"[Bookshop] Timeout syncing order {unique_order_id} to admin dashboard"
                )
                flash("Order placed, but sync to admin dashboard timed out.", "warning")
            except Exception as e:
                current_app.logger.exception(
                    f"[Bookshop] Error syncing order {unique_order_id} to admin dashboard: {e}"
                )
                flash(f"Order placed, but error syncing to admin dashboard.", "warning")

            flash(
                f"Order placed successfully. Your Order ID is {unique_order_id}. "
                f"You will pay on delivery.", 
                "success"
            )
            session.pop('cart', None)
            return redirect(url_for('main.order_success', order_id=unique_order_id))

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
        metadata = data.get('metadata', {})
        cart_items = metadata.get('cart', [])
        phone = metadata.get('phone', '')
        unique_order_id = metadata.get('order_id')

        if not unique_order_id or not cart_items:
            flash("Missing order details. Contact support.", "danger")
            return redirect(url_for('main.home'))

        order = Order(
            order_id=unique_order_id,
            user_id=metadata.get('user_id'),
            full_name=metadata.get('full_name', 'Customer'),
            email=data['customer'].get('email', 'no-reply@example.com'),
            address=metadata.get('address', ''),
            total_amount=data['amount'] / 100,
            payment_method='paystack',
            status='paid'
        )
        db.session.add(order)
        db.session.flush()

        order_items_data = []
        for item in cart_items:
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=item['product_id'],
                quantity=int(item['quantity']),
                price=float(item['price'])
            ))
            order_items_data.append({
                'product_id': item['product_id'],
                'product_name': item['product_name'],
                'quantity': int(item['quantity']),
                'price': float(item['price']),
                'original_price': float(item.get('original_price', item['price']))  # fallback
            })

        db.session.commit()

        # Compute subtotal & discount safely
        subtotal = sum(i['original_price'] * i['quantity'] for i in order_items_data)
        discount = sum((i['original_price'] - i['price']) * i['quantity'] for i in order_items_data)

        # Sync order to Learning Platform
        try:
            api_data = {
                'order_id': unique_order_id,
                'user_id': metadata.get('user_id'),
                'full_name': order.full_name,
                'email': order.email,
                'address': order.address,
                'total_amount': order.total_amount,
                'payment_method': 'paystack',
                'items': [
                    {
                        'product_id': i['product_id'],
                        'product_name': i['product_name'],
                        'quantity': i['quantity'],
                        'price': i['price']
                    } for i in order_items_data
                ]
            }
            api_headers = {
                'Authorization': f'Bearer {os.getenv("API_TOKEN")}',
                'Content-Type': 'application/json'
            }
            api_res = requests.post(
                f'{os.getenv('API_BASE_URL')}/orders',
                json=api_data,
                headers=api_headers,
                timeout=10
            )
            if api_res.status_code != 201:
                current_app.logger.warning(f"[API SYNC] Failed: {api_res.status_code} - {api_res.text}")
        except Exception as e:
            current_app.logger.error(f"[API SYNC] Exception during Paystack sync: {e}")

        send_order_email(
            to=order.email,
            full_name=order.full_name,
            order_id=unique_order_id,
            items=order_items_data,
            total=order.total_amount,
            payment_method="Paystack",
            address=order.address,
            phone=phone,
            order_date=datetime.now().strftime('%d %B %Y %I:%M%p').lower(),
            subtotal=subtotal,
            discount=discount
        )

        session.pop('cart', None)
        session.pop('paid_cart_items', None)

        return render_template("order_success.html", order=order, order_id=order.order_id)

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
