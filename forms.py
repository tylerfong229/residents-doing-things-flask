from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectMultipleField, widgets
from flask import session


class AccessCodeForm(FlaskForm):
    accesscode = StringField("Amion Access Code")
    submit = SubmitField("Go")


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


def CreateNameDropDown(names: list):
    string_of_names = "-=-".join(names)

    class SimpleForm(FlaskForm):
        list_of_strings = string_of_names.split("-=-")
        files = [(x, x) for x in list_of_strings]
        names = MultiCheckboxField("Label", choices=files)

    return SimpleForm()
