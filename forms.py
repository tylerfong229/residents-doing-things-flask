from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField


class AccessCodeForm(FlaskForm):
    accesscode = StringField("Amion Access Code")
    submit = SubmitField("Go")
