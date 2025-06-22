import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Default secret key for development if not set in .env
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')

    # SQLite DB absolute path
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'realmind_ecommerce.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Directory for product image uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

    # Token for authenticating product sync API from learning platform
    API_TOKEN = os.getenv('API_TOKEN', 'default-token')

    # Custom session cookie name to avoid conflict with other apps
    SESSION_COOKIE_NAME = 'ecommerce_session'
