from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
from flask_mail import Mail

# Load environment variables
load_dotenv()

# Initialize extensions (without app yet)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__)

    # Load config
    app.config.from_object('config.Config')
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
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
