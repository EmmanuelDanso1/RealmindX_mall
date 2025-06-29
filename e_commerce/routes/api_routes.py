from flask import request, jsonify, Blueprint, current_app
from werkzeug.utils import secure_filename
from e_commerce.models import Product, Category, InfoDocument
from e_commerce import db
import os
from e_commerce.utils.helpers import allowed_file, allowed_image_file
import traceback

API_TOKEN = os.getenv("API_TOKEN")

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/products', methods=['POST'])
def receive_product():
    token = request.headers.get('Authorization')
    if not token or token != f"Bearer {API_TOKEN}":
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    try:
        category_name = data.get('category', '').strip().title()
        if not category_name:
            return jsonify({'error': 'Category is required'}), 400

        # ✅ Find or create category
        category = Category.query.filter_by(name=category_name).first()
        if not category:
            category = Category(name=category_name)
            db.session.add(category)
            db.session.commit()

        # ✅ Create product with new metadata fields
        product = Product(
            name=data['name'],
            description=data['description'],
            price=data['price'],
            image_filename=data.get('image_filename'),
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

        return jsonify({'message': 'Product synced', 'id': product.id}), 201

    except Exception as e:
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
        product.in_stock = data.get('in_stock', True)
        product.image_filename = data.get('image_filename', product.image_filename)

        # ✅ Optional fields
        product.author = data.get('author')
        product.brand = data.get('brand')
        product.grade = data.get('grade')
        product.level = data.get('level')
        product.subject = data.get('subject')

        # ✅ Handle category update (optional)
        category_name = data.get('category', '').strip().title()
        if category_name:
            category = Category.query.filter_by(name=category_name).first()
            if not category:
                category = Category(name=category_name)
                db.session.add(category)
                db.session.commit()
            product.category_id = category.id

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
