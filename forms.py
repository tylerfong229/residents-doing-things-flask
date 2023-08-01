from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectMultipleField, widgets
from flask import session


class AccessCodeForm(FlaskForm):
    accesscode = StringField("Amion Access Code")
    submit = SubmitField("Go")
