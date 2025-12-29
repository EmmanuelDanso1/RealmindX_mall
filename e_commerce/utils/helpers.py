import datetime
import random
from e_commerce.models import Order
from flask import request, jsonify, current_app
import os


ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def generate_random_order_id():
    date_str = datetime.datetime.now().strftime('%d%m%y')
    random_digits = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    return f"RmxEdu{date_str}{random_digits}"

def get_random_unique_order_id():
    while True:
        new_id = generate_random_order_id()
        if not Order.query.filter_by(order_id=new_id).first():
            return new_id


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FLIERS_UPLOAD_DIR = os.path.join(BASE_DIR, 'e_commerce', 'static', 'uploads', 'fliers')
