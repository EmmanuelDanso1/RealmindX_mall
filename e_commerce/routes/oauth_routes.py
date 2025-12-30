from flask import Blueprint, redirect, url_for, session, flash, current_app
from flask_login import login_user, current_user
from authlib.integrations.flask_client import OAuth
from e_commerce.models import User
from extensions import db
from extensions import limiter
import os
import logging

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
@limiter.limit("10 per hour")
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
        full_name = user_info.get('name')

        if not email or not google_id:
            flash('Required information not provided by Google.', 'danger')
            return redirect(url_for('auth.login'))

        user = User.query.filter_by(email=email).first()

        if user:
            # Link Google account if not already linked
            if not user.google_id:
                user.google_id = google_id
                user.is_oauth_user = True
                db.session.commit()

            current_app.logger.info(f"[OAuth] Existing user logged in: {email}")

        else:
            # Create new OAuth user
            user = User(
                full_name=full_name or email.split('@')[0],
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
