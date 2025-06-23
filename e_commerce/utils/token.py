# utils/token.py

from itsdangerous import URLSafeTimedSerializer
from flask import current_app

def generate_verification_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='email-verify')

def confirm_verification_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='email-verify', max_age=expiration)
    except Exception:
        return None
    return email
