from flask import request, jsonify, Blueprint, current_app, session
from werkzeug.utils import secure_filename
from flask_login import login_user, login_required, logout_user
from e_commerce import db, mail
import os
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from flask import request, redirect, url_for, flash, render_template
from flask_login import login_user
from werkzeug.security import check_password_hash
from werkzeug.security import check_password_hash, generate_password_hash
from e_commerce.models import User
from e_commerce.forms import UserSignupForm, LoginForm, PasswordResetForm, PasswordResetRequestForm

auth_bp = Blueprint('auth', __name__)

s = URLSafeTimedSerializer(os.getenv('SECRET_KEY'))


@auth_bp.route('/user/signup', methods=['GET', 'POST'])
def user_signup():
    form = UserSignupForm()
    
    if form.validate_on_submit():
        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email:
            flash('Email already registered. Please log in.', 'danger')
            return redirect(url_for('auth.login'))

        existing_username = User.query.filter_by(username=form.username.data).first()
        if existing_username:
            flash('Username already taken. Please choose another.', 'danger')
            return redirect(url_for('auth.user_signup'))

        hashed_password = generate_password_hash(form.password.data)
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('cart.checkout'))

    return render_template('auth/signup.html', form=form)

@auth_bp.route('/user/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            next_page = session.pop('next', None)
            return redirect(url_for(next_page)) if next_page else redirect(url_for('cart.checkout'))
        flash('Invalid credentials', 'danger')
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))  # adjust as needed

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = s.dumps(user.email, salt='password-reset-salt')
            reset_link = url_for('auth.reset_password', token=token, _external=True)

            try:
                msg = Message(
                    subject="Password Reset Request",
                    sender=os.getenv('MAIL_USERNAME'),
                    recipients=[user.email]
                )
                msg.body = f"""
Hello {user.username},

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
                print(f"Email sending failed: {e}")
                flash('Could not send email. Please try again later.', 'danger')
        else:
            flash('No account found with that email.', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', form=form)

# password reset
@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600)
    except:
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=email).first_or_404()
        user.set_password(form.password.data)  # Ensure `set_password()` hashes and sets the password
        db.session.commit()
        flash('Your password has been updated.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form)