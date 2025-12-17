from flask import Blueprint, redirect, url_for, session, flash, current_app
from flask_login import login_user, current_user
from authlib.integrations.flask_client import OAuth
from e_commerce.models import User
from extensions import db
import os

oauth_bp = Blueprint('oauth', __name__)
oauth = OAuth()

def init_oauth(app):
    """Initialize OAuth with the Flask app"""
    oauth.init_app(app)
    
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
    
    app.logger.info("[Bookshop OAuth] Google OAuth initialized")


@oauth_bp.route('/login/google')
def google_login():
    """Initiate Google OAuth login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.shop'))
    
    redirect_uri = url_for('oauth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@oauth_bp.route('/callback/google')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            flash('Failed to get user information from Google.', 'danger')
            return redirect(url_for('auth.login'))
        
        email = user_info.get('email')
        google_id = user_info.get('sub')
        
        if not email:
            flash('Email not provided by Google.', 'danger')
            return redirect(url_for('auth.login'))
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            if not user.google_id:
                user.google_id = google_id
                db.session.commit()
            current_app.logger.info(f"[OAuth] Existing user logged in: {email}")
        else:
            username = email.split('@')[0]
            base_username = username
            counter = 1
            
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                username=username,
                email=email,
                google_id=google_id,
                password=None,
                is_oauth_user=True
            )
            db.session.add(user)
            db.session.commit()
            
            current_app.logger.info(f"[OAuth] New user created: {email}")
            flash('Account created successfully with Google!', 'success')
        
        login_user(user)
        return redirect(url_for('main.shop'))
        
    except Exception as e:
        current_app.logger.exception(f"[OAuth] Error: {e}")
        flash('An error occurred during Google login.', 'danger')
        return redirect(url_for('auth.login'))