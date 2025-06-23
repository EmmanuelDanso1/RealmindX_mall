# Flask routes for cart functionality
from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from e_commerce.models import Product

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
def checkout():
    cart = get_cart()
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('main.home'))

    items = []
    total = 0

    for product_id, item in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            quantity = item['quantity']
            total += product.price * quantity
            items.append({'product': product, 'quantity': quantity})

    if request.method == 'POST':
        # Implement payment integration here
        session.pop('cart', None)
        flash("Checkout successful!", "success")
        return redirect(url_for('main.home'))

    return render_template('checkout.html', cart=items, total=total)
