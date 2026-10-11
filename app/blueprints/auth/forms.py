from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models import User


class LoginForm(FlaskForm):
    """User login form."""
    email = StringField("Email Address", validators=[
        DataRequired(message="Email is required."),
        Email(message="Please provide a valid email address.")
    ])
    password = PasswordField("Password", validators=[
        DataRequired(message="Password is required.")
    ])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Log In")


class SignupForm(FlaskForm):
    """New user registration form."""
    name = StringField("Full Name", validators=[
        DataRequired(message="Name is required."),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters.")
    ])
    email = StringField("Email Address", validators=[
        DataRequired(message="Email is required."),
        Email(message="Please provide a valid email address.")
    ])
    password = PasswordField("Password", validators=[
        DataRequired(message="Password is required."),
        Length(min=6, message="Password must be at least 6 characters.")
    ])
    confirm_password = PasswordField("Confirm Password", validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo("password", message="Passwords must match.")
    ])
    submit = SubmitField("Create Account")

    def validate_email(self, field):
        """Ensure email is not already taken."""
        user = User.query.filter_by(email=field.data.strip().lower()).first()
        if user:
            raise ValidationError("This email address is already registered.")
