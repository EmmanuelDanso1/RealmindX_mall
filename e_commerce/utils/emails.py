from flask_mail import Message
from extensions import mail


def send_admin_order_email(order, items):
    subject = f"New Order Received – {order.order_id}"

    body = f"""
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
        body += f"- {item['product_name']} x {item['quantity']} (GH₵ {item['price']})\n"

    body += "\nPlease log in to the admin dashboard to process this order."

    msg = Message(
        subject=subject,
        recipients=["realmindxgh@gmail.com"],  # ADMIN EMAIL
        body=body
    )

    mail.send(msg)
