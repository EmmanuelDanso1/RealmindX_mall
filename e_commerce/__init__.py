from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize extensions (without app yet)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Load config
    app.config.from_object('config.Config')

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Route name for login

    # Import User after db is initialized
    from e_commerce.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        # Skip admin-style IDs like 'admin:1'
        if isinstance(user_id, str) and user_id.startswith("admin:"):
            return None
        try:
            return User.query.get(int(user_id))
        except ValueError:
            return None


    # Register blueprints
    from .routes.api_routes import api_bp
    from .routes.main_routes import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    return app
