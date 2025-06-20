from flask import request, jsonify, Blueprint, current_app
from werkzeug.utils import secure_filename
from e_commerce.models import Product
from e_commerce import db
import os

API_TOKEN = os.getenv("API_TOKEN")

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/products', methods=['POST'])
def receive_product():
    token = request.headers.get('Authorization')
    if not token or token != f"Bearer {API_TOKEN}":
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    try:
        product = Product(
            name=data['name'],
            description=data['description'],
            price=data['price'],
            image_filename=data['image_filename']
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({'message': 'Product synced'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@api_bp.route('/api/upload-image', methods=['POST'])
def upload_image():
    token = request.headers.get('Authorization')
    if token != f"Bearer {os.getenv('API_TOKEN')}":
        return jsonify({'error': 'Unauthorized'}), 401

    image = request.files.get('image')
    if not image:
        return jsonify({'error': 'No file received'}), 400

    filename = secure_filename(image.filename)
    upload_path = os.path.join(current_app.root_path, 'static/uploads', filename)
    image.save(upload_path)
    return jsonify({'message': 'Image uploaded'}), 201
