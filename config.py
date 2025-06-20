import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Use a default secret key for development if not set
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')

    # Absolute path to the SQLite DB file (recommended for consistency)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'ecommerce.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Token used for protecting incoming product sync API
    API_TOKEN = os.getenv('API_TOKEN')
