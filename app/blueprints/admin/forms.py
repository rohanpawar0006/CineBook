from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, DecimalField, DateTimeLocalField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, URL


class MovieForm(FlaskForm):
    """Admin form to add or edit a movie."""
    title = StringField("Title", validators=[
        DataRequired(message="Title is required."),
        Length(max=150)
    ])
    description = TextAreaField("Description", validators=[
        DataRequired(message="Description is required.")
    ])
    language = StringField("Language", validators=[
        DataRequired(message="Language is required."),
        Length(max=50)
    ])
    genre = StringField("Genre", validators=[
        DataRequired(message="Genre is required."),
        Length(max=50)
    ])
    duration_min = IntegerField("Duration (minutes)", validators=[
        DataRequired(message="Duration is required."),
        NumberRange(min=1, max=600, message="Duration must be between 1 and 600 minutes.")
    ])
    poster_url = StringField("Poster Image URL", validators=[
        Optional(),
        Length(max=500)
    ])
    submit = SubmitField("Save Movie")


class ShowForm(FlaskForm):
    """Admin form to schedule a screening show."""
    movie_id = SelectField("Movie", coerce=int, validators=[DataRequired()])
    screen_id = SelectField("Auditorium / Screen", coerce=int, validators=[DataRequired()])
    start_time = DateTimeLocalField("Start Date & Time", format="%Y-%m-%dT%H:%M", validators=[
        DataRequired(message="Show start time is required.")
    ])
    price = DecimalField("Price ($)", places=2, validators=[
        DataRequired(message="Price is required."),
        NumberRange(min=0.01, message="Price must be greater than zero.")
    ])
    submit = SubmitField("Schedule Show")
