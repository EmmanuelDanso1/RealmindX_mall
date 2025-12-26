from flask import render_template, current_app
from flask_mail import Message
from extensions import mail
import os


def send_admin_order_email(order, items):
    subject = f"New Order Received – {order.order_id}"

    message = f"""
    A new order has been placed.

    Order ID: {order.order_id}
    Customer: {order.full_name}
    Phone: {order.phone}
    Email: {order.email}
    Payment Method: {order.payment_method}
    Total: GH₵ {order.total_amount}

    Items:
    """

    for item in items:
        message += f"""
        - {item['product_name']} x {item['quantity']} (GH₵ {item['price']})
        """

    message += """

    Please log in to the admin dashboard to process this order.
    """

    send_mail(
        subject=subject,
        recipients=["realmindxgh@gmail.com"],  # ADMIN EMAIL
        body=message
    )
