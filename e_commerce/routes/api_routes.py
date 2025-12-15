from flask import request, jsonify, Blueprint, current_app
from werkzeug.utils import secure_filename
from e_commerce.models import Product, Category, InfoDocument, OrderItem, Order, PromotionFlier, NewsletterSubscriber
from extensions import db
import os
import json
from e_commerce.utils.helpers import allowed_file, allowed_image_file, generate_random_order_id
from flask import send_from_directory
import traceback
import logging

logger = logging.getLogger(__name__)

API_TOKEN = os.getenv("API_TOKEN")

api_bp = Blueprint('api', __name__)

@api_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@api_bp.route('/api/products', methods=['POST'])
def receive_product():
    logger.info("/api/products called")

    token = request.headers.get('Authorization')
    if not token or token != f"Bearer {API_TOKEN}":
        logger.warning("Unauthorized request")
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # ---------- PRODUCT DATA ----------
        data_json = request.form.get('data')
        if not data_json:
            logger.error("Missing product data")
            return jsonify({'error': 'Missing product data'}), 400

        data = json.loads(data_json)
        logger.info(f"Product data received: {data.get('name')}")

        # ---------- CATEGORY ----------
        category_name = data.get('category', '').strip().title()
        if not category_name:
            logger.error("Category missing")
            return jsonify({'error': 'Category is required'}), 400

        category = Category.query.filter_by(name=category_name).first()
        if not category:
            category = Category(name=category_name)
            db.session.add(category)
            db.session.commit()
            logger.info(f"Category created: {category_name}")
        else:
            logger.info(f"Category found: {category_name}")

        # ---------- IMAGE ----------
        file = request.files.get('image')
        if not file:
            logger.error("Image file missing in request")
            return jsonify({'error': 'Image file is required'}), 400

        logger.info(
            f"Image received: filename={file.filename}, "
            f"content_type={file.content_type}"
        )

        filename = secure_filename(file.filename)
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        upload_path = os.path.join(upload_dir, filename)

        try:
            os.makedirs(upload_dir, exist_ok=True)
            file.save(upload_path)
            logger.info(f"Image saved at: {upload_path}")
            logger.info(f"Image size: {os.path.getsize(upload_path)} bytes")
        except Exception as img_err:
            logger.exception(f"Image save failed: {img_err}")
            return jsonify({'error': 'Failed to save image'}), 500

        image_url = f"https://bookshop.realmindxgh.com/static/uploads/{filename}"
        logger.info(f"Image URL generated: {image_url}")

        # ---------- PRODUCT ----------
        product = Product(
            name=data['name'],
            description=data['description'],
            price=data['price'],
            discount_percentage=data.get('discount_percentage', 0.0),
            image_filename=filename,
            image_url=image_url,
            in_stock=data.get('in_stock', True),
            category_id=category.id,
            author=data.get('author'),
            brand=data.get('brand'),
            grade=data.get('grade'),
            level=data.get('level'),
            subject=data.get('subject')
        )

        db.session.add(product)
        db.session.commit()

        logger.info(f"Product saved: id={product.id}, name={product.name}")

        return jsonify({
            'message': 'Product synced',
            'id': product.id,
            'image_url': image_url
        }), 201

    except Exception as e:
        logger.exception("Unexpected error during product sync")
        return jsonify({'error': str(e)}), 400

# pagination
@api_bp.route('/api/products', methods=['GET'])
def get_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)  # default 10

    query = Product.query.order_by(Product.date_created.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    products_data = []
    for product in pagination.items:
        products_data.append({
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'price': product.price,
            'discount_percentage': product.discount_percentage,
            'image_filename': product.image_filename,
            'in_stock': product.in_stock,
            'author': product.author,
            'brand': product.brand,
            'grade': product.grade,
            'level': product.level,
            'subject': product.subject,
            'category': product.category.name if product.category else None,
            'date_created': product.date_created.strftime('%Y-%m-%d %H:%M:%S')
        })

    return jsonify({
        'products': products_data,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page,
        'per_page': pagination.per_page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
    })

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

# edit product
@api_bp.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product_api(product_id):
    token = request.headers.get('Authorization')
    if not token or token != f"Bearer {API_TOKEN}":
        return jsonify({'error': 'Unauthorized'}), 401

    product = Product.query.get_or_404(product_id)
    data = request.json

    try:
        product.name = data['name']
        product.description = data['description']
        product.price = data['price']
        product.discount_percentage = data.get('discount_percentage', 0.0)
        product.in_stock = data.get('in_stock', True)
        product.image_filename = data.get('image_filename', product.image_filename)

        # Optional fields
        product.author = data.get('author')
        product.brand = data.get('brand')
        product.grade = data.get('grade')
        product.level = data.get('level')
        product.subject = data.get('subject')

        # Handle category update (optional)
        category_name = data.get('category', '').strip().title()
        if category_name:
            category = Category.query.filter_by(name=category_name).first()
            if not category:
                category = Category(name=category_name)
                db.session.add(category)
                db.session.commit()
            product.category_id = category.id
        file = request.files.get('image')
        if file:
            filename = secure_filename(file.filename)
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads', filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)
            product.image_filename = filename

        db.session.commit()
        return jsonify({'message': 'Product updated'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400



# delete product
@api_bp.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product_api(product_id):
    token = request.headers.get('Authorization')
    if not token or token != f"Bearer {API_TOKEN}":
        return jsonify({'error': 'Unauthorized'}), 401

    product = Product.query.get_or_404(product_id)

    try:
        # Optional: Check for order dependency
        used = OrderItem.query.filter_by(product_id=product.id).first()
        if used:
            return jsonify({'error': 'Product is used in orders'}), 400

        db.session.delete(product)
        db.session.commit()
        return jsonify({'message': f'Product {product.name} deleted'}), 200

    except Exception as e:
        return jsonify({'error': 'Failed to delete product', 'details': str(e)}), 500



# recieve  info from learning platform
@api_bp.route('/api/info', methods=['POST'])
def receive_info_document():
    # Check Authorization header
    token = request.headers.get('Authorization')
    if not token or token != f"Bearer {os.getenv('API_TOKEN')}":
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        #  Extract form data and files
        title = request.form.get('title', '').strip()
        source = request.form.get('source', '').strip()
        file = request.files.get('file')
        image = request.files.get('image')

        # Basic validation
        if not title or not source or not file:
            return jsonify({'error': 'Title, source, and file are required'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid document format. Allowed: pdf, doc, docx'}), 400

        # Ensure upload directory exists
        upload_dir = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)

        # Save document
        doc_filename = secure_filename(file.filename)
        doc_path = os.path.join(upload_dir, doc_filename)
        file.save(doc_path)

        # Save image if present
        image_filename = None
        if image and image.filename:
            if not allowed_image_file(image.filename):
                return jsonify({'error': 'Invalid image format. Allowed: jpg, jpeg, png, gif, webp'}), 400

            image_filename = secure_filename(image.filename)
            image_path = os.path.join(upload_dir, image_filename)
            image.save(image_path)

        # Save info to database
        info_doc = InfoDocument(
            title=title,
            source=source,  # Can be plain text or a URL
            filename=doc_filename,
            image=image_filename
        )
        db.session.add(info_doc)
        db.session.commit()

        return jsonify({'message': 'Info uploaded successfully', 'id': info_doc.id}), 201

    except Exception as e:
        print("API Upload Error:", e)
        return jsonify({'error': str(e)}), 400
    
# edit document
@api_bp.route('/api/info/<int:id>', methods=['PUT', 'PATCH'])
def edit_info_document(id):
    # Check Authorization header
    token = request.headers.get('Authorization')
    if not token or token != f"Bearer {os.getenv('API_TOKEN')}":
        return jsonify({'error': 'Unauthorized'}), 401

    info_doc = InfoDocument.query.get_or_404(id)

    try:
        title = request.form.get('title', info_doc.title).strip()
        source = request.form.get('source', info_doc.source).strip()
        file = request.files.get('file')
        image = request.files.get('image')

        upload_dir = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)

        # Update file if new file is provided
        if file:
            if not allowed_file(file.filename):
                return jsonify({'error': 'Invalid document format. Allowed: pdf, doc, docx'}), 400
            doc_filename = secure_filename(file.filename)
            doc_path = os.path.join(upload_dir, doc_filename)
            file.save(doc_path)
            info_doc.filename = doc_filename

        # Update image if new image provided
        if image and image.filename:
            if not allowed_image_file(image.filename):
                return jsonify({'error': 'Invalid image format. Allowed: jpg, jpeg, png, gif, webp'}), 400
            image_filename = secure_filename(image.filename)
            image_path = os.path.join(upload_dir, image_filename)
            image.save(image_path)
            info_doc.image = image_filename

        info_doc.title = title
        info_doc.source = source

        db.session.commit()

        return jsonify({'message': 'Info document updated successfully'}), 200

    except Exception as e:
        print("API Edit Error:", e)
        return jsonify({'error': str(e)}), 400

# delete
@api_bp.route('/api/info/<int:id>', methods=['DELETE'])
def delete_info_document(id):
    # Check Authorization header
    token = request.headers.get('Authorization')
    if not token or token != f"Bearer {os.getenv('API_TOKEN')}":
        return jsonify({'error': 'Unauthorized'}), 401

    info_doc = InfoDocument.query.get_or_404(id)

    try:
        # Optionally delete files from storage
        upload_dir = current_app.config['UPLOAD_FOLDER']

        if info_doc.filename:
            file_path = os.path.join(upload_dir, info_doc.filename)
            if os.path.exists(file_path):
                os.remove(file_path)

        if info_doc.image:
            image_path = os.path.join(upload_dir, info_doc.image)
            if os.path.exists(image_path):
                os.remove(image_path)

        db.session.delete(info_doc)
        db.session.commit()

        return jsonify({'message': 'Info document deleted successfully'}), 200

    except Exception as e:
        print("API Delete Error:", e)
        return jsonify({'error': str(e)}), 400

# update for status check
@api_bp.route('/api/orders/<string:order_id>/status', methods=['POST'])
def update_order_status_api(order_id):
    # Use original_order_id here, which is a string
    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        return jsonify({'error': 'Order not found'}), 404

    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({'error': 'Missing status'}), 400

    new_status = data['status']
    if new_status not in ['Received', 'In Process', 'Delivered']:
        return jsonify({'error': 'Invalid status'}), 400

    order.status = new_status
    db.session.commit()

    return jsonify({'success': True, 'status': new_status})


# recieves post api
@api_bp.route('/api/fliers', methods=['POST'])
def receive_flier():
    # Check Authorization header 
    token = request.headers.get('Authorization')
    if not token or token != f"Bearer {os.getenv('API_TOKEN')}":
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Extract title (optional) and image (required)
        title = request.form.get('title', '').strip()
        image_file = request.files.get('image')  # ✅ FIXED: match the input field name

        if not image_file:
            return jsonify({'error': 'Image file is required'}), 400

        if not allowed_image_file(image_file.filename):
            return jsonify({'error': 'Invalid image format. Allowed: jpg, jpeg, png, gif, webp'}), 400

        # Ensure upload directory exists
        flier_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'fliers')
        os.makedirs(flier_dir, exist_ok=True)

        # Save the image
        image_filename = secure_filename(image_file.filename)
        image_path = os.path.join(flier_dir, image_filename)
        image_file.save(image_path)

        # Save to DB
        flier = PromotionFlier(title=title, image_filename=image_filename)
        db.session.add(flier)
        db.session.commit()

        return jsonify({'message': 'Flier received', 'id': flier.id}), 201

    except Exception as e:
        print("Flier API Error:", e)
        return jsonify({'error': str(e)}), 400

@api_bp.route('/api/fliers/<int:flier_id>', methods=['PUT'])
def update_flier(flier_id):
    token = request.headers.get('Authorization')
    if not token or token != f"Bearer {os.getenv('API_TOKEN')}":
        return jsonify({'error': 'Unauthorized'}), 401

    flier = PromotionFlier.query.get_or_404(flier_id)
    try:
        title = request.form.get('title', '').strip()
        image_file = request.files.get('image')

        if title:
            flier.title = title

        if image_file:
            if not allowed_image_file(image_file.filename):
                return jsonify({'error': 'Invalid image format'}), 400

            # Delete old image
            old_path = os.path.join(current_app.root_path, 'static', 'uploads', 'fliers', flier.image_filename)
            if os.path.exists(old_path):
                os.remove(old_path)

            # Save new image
            image_filename = secure_filename(image_file.filename)
            new_path = os.path.join(current_app.root_path, 'static', 'uploads', 'fliers', image_filename)
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            image_file.save(new_path)
            flier.image_filename = image_filename

        db.session.commit()
        return jsonify({'message': 'Flier updated'}), 200

    except Exception as e:
        print("Update Flier Error:", e)
        return jsonify({'error': str(e)}), 400

@api_bp.route('/api/fliers/<int:flier_id>', methods=['DELETE'])
def delete_flier(flier_id):
    token = request.headers.get('Authorization')
    if not token or token != f"Bearer {os.getenv('API_TOKEN')}":
        return jsonify({'error': 'Unauthorized'}), 401

    flier = PromotionFlier.query.get_or_404(flier_id)

    try:
        # Delete the image file from disk
        image_path = os.path.join(current_app.root_path, 'static', 'uploads', 'fliers', flier.image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

        db.session.delete(flier)
        db.session.commit()
        return jsonify({'message': 'Flier deleted'}), 200

    except Exception as e:
        print("Delete Flier Error:", e)
 
        return jsonify({'error': str(e)}), 400
    
@api_bp.route('/api/newsletter-subscribers')
def get_newsletter_subscribers():
    token = request.headers.get('Authorization')
    if not token or token != f"Bearer {API_TOKEN}":
        return jsonify({'error': 'Unauthorized'}), 401

    subscribers = NewsletterSubscriber.query.filter_by(is_verified=True).all()
    emails = [s.email for s in subscribers]
    return jsonify({'subscribers': emails}), 200
