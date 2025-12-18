import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from sqlalchemy import MetaData
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from urllib.parse import quote_plus
# Constraint naming convention for Alembic
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)

# Load Redis password from environment variable
# using quote_plus for encoding the "@" character
REDIS_PASSWORD = quote_plus(os.getenv("REDIS_PASSWORD", ""))

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    # testing/development
    # storage_uri="memory://"
    # production
    storage_uri=f"redis://:{REDIS_PASSWORD}@127.0.0.1:6379/0"
)

# Initialize extensions with naming convention
db = SQLAlchemy(metadata=metadata)
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
