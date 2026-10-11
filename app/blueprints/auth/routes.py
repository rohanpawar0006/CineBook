import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlsplit
from app.extensions import db
from app.models import User
from app.blueprints.auth.forms import LoginForm, SignupForm

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """User registration view."""
    if current_user.is_authenticated:
        return redirect(url_for("movies.index"))

    form = SignupForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            role="user"
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        logger.info("New user registered successfully: %s", user.email)
        flash("Your account has been created! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/signup.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login view."""
    if current_user.is_authenticated:
        return redirect(url_for("movies.index"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            logger.info("User logged in: %s", user.email)
            flash(f"Welcome back, {user.name}!", "success")

            next_page = request.args.get("next")
            # Ensure open redirect prevention
            if not next_page or urlsplit(next_page).netloc != "":
                next_page = url_for("movies.index")
            return redirect(next_page)
        else:
            logger.warning("Failed login attempt for: %s", email)
            flash("Invalid email or password. Please try again.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST", "GET"])
@login_required
def logout():
    """Log out current user."""
    user_email = current_user.email
    logout_user()
    logger.info("User logged out: %s", user_email)
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("movies.index"))
