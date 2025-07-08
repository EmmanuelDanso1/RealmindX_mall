import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Default secret key for development if not set in .env
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')

    # SQLite DB absolute path
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'realmindxEdugh_mall.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Directory for product image uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'e_commerce', 'static', 'uploads')

    # Token for authenticating product sync API from learning platform
    API_TOKEN = os.getenv('API_TOKEN', 'default-token')

    # Custom session cookie name to avoid conflict with other apps
    SESSION_COOKIE_NAME = 'ecommerce_session'
    
    # mail configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') 
    MAIL_DEFAULT_SENDER = MAIL_USERNAME
    
    # Paystack config
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
    PAYSTACK_INITIALIZE_URL = 'https://api.paystack.co/transaction/initialize'
    PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY')

