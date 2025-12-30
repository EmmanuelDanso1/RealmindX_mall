from flask import request, jsonify, Blueprint, current_app, session
from werkzeug.utils import secure_filename
from flask_login import login_user, login_required, logout_user
from extensions import db, mail
import os
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from flask import request, redirect, url_for, flash, render_template
from flask_login import login_user
from werkzeug.security import check_password_hash
from werkzeug.security import check_password_hash, generate_password_hash
from e_commerce.models import User
from e_commerce.forms import UserSignupForm, LoginForm, PasswordResetForm, PasswordResetRequestForm
from urllib.parse import urlparse, urljoin
# rate limiting
from extensions import limiter

auth_bp = Blueprint('auth', __name__)

s = URLSafeTimedSerializer(os.getenv('SECRET_KEY'))

@auth_bp.route('/user/signup', methods=['GET', 'POST'])
def user_signup():
    form = UserSignupForm()
    
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered. Please log in.', 'danger')
            return redirect(url_for('auth.login'))


        new_user = User(
            full_name=form.full_name.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data),
            is_oauth_user=False
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash('Account created successfully!', 'success')

        # Redirect to shop
        return redirect(url_for('main.shop'))

    return render_template('auth/signup.html', form=form)


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc



@auth_bp.route('/user/login', methods=['GET', 'POST'])
@limiter.limit("5 per 10 minutes")
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if not user:
            flash('Invalid credentials', 'danger')
            return render_template('auth/login.html', form=form)

        # Block OAuth users from password login
        if user.is_oauth_user:
            flash('Please sign in using Google', 'warning')
            return redirect(url_for('auth.login'))

        #  Normal password check
        if not user.password or not check_password_hash(user.password, form.password.data):
            flash('Invalid credentials', 'danger')
            return render_template('auth/login.html', form=form)

        login_user(user)

        # Sync session cart to database
        from e_commerce.routes.cart_routes import sync_session_to_db
        sync_session_to_db()

        next_page = request.args.get('next') or session.pop('next', None)
        if next_page and is_safe_url(next_page):
            return redirect(next_page)

        return redirect(url_for('main.shop'))

    return render_template('auth/login.html', form=form)



@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = PasswordResetRequestForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user:
            if user.is_oauth_user:
                flash('This account uses Google sign-in. Please log in with Google.', 'warning')
                return redirect(url_for('auth.login'))

            token = s.dumps(user.email, salt='password-reset-salt')
            reset_link = url_for('auth.reset_password', token=token, _external=True)

            try:
                msg = Message(
                    subject="Password Reset Request",
                    sender=os.getenv('MAIL_USERNAME'),
                    recipients=[user.email]
                )
                msg.body = f"""
Hello {user.full_name},

We received a request to reset your password.

Click the link below to reset it:
{reset_link}

If you did not request this, simply ignore this email.

Regards,
RealmIndx Support Team
"""
                mail.send(msg)
                flash('Password reset link has been sent to your email.', 'info')
            except Exception as e:
                current_app.logger.error(f"Email sending failed: {e}")
                flash('Could not send email. Please try again later.', 'danger')
        else:
            flash('No account found with that email.', 'danger')

        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', form=form)
