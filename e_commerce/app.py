from flask import Flask, session,request
from dotenv import load_dotenv
import os
from extensions import db, migrate, login_manager, mail
import logging
from logging.handlers import RotatingFileHandler
from e_commerce.routes.oauth_routes import oauth_bp, init_oauth

# Load environment variables
load_dotenv()


def create_app():
    app = Flask(__name__)

    # mail config
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

    
    # Load config
    app.config.from_object('config.Config')
    
    # ---------------------------
    # BASIC LOGGING (console)
    # ---------------------------
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )

    # ---------------------------
    # FILE LOGGING (production)
    # ---------------------------
    if not app.debug and not app.testing:
        log_dir = os.path.join(app.root_path, 'logs')
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, 'bookshop.log')

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10240,   # 10KB
            backupCount=10
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        ))

        # Prevent duplicate handlers
        if not any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):
            app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info(" Bookshop application started")

    # ---------------------------
    # LOG STATIC IMAGE REQUESTS
    # ---------------------------
    @app.before_request
    def log_image_requests():
        if request.path.startswith('/static/uploads/'):
            current_app.logger.info(f"Image requested: {request.path}")

    # Initialize OAuth
    init_oauth(app)
    
    # Register blueprint
    app.register_blueprint(oauth_bp, url_prefix='/oauth')
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # Initialize extensions
    try:
        db.init_app(app)
        print("Database connected successfully.")
    except Exception as e:
        print(f"Database connection failed: {e}")
    
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    mail.init_app(app)

    # Import User after db is initialized
    from e_commerce.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        if isinstance(user_id, str) and user_id.startswith("admin:"):
            return None
        try:
            return User.query.get(int(user_id))
        except ValueError:
            return None

    # Register blueprints
    from .routes.api_routes import api_bp
    from .routes.main_routes import main_bp
    from .routes.cart_routes import cart_bp
    from .routes.auth_routes import auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(auth_bp)

    # Cart Totals
    @app.context_processor
    def cart_info():
        cart = session.get('cart', {})
        total_items = sum(item['quantity'] for item in cart.values())
        total_amount = sum(item['price'] * item['quantity'] for item in cart.values())
        return dict(cart_item_count=total_items, cart_total=total_amount)

    # Inject categories globally (for navbar dropdown)
    from e_commerce.models import Category

    @app.context_processor
    def inject_categories():
        return {
            'categories': Category.query.order_by(Category.name).all()
        }

    return app
