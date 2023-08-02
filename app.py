from flask import Flask, render_template, request, redirect, url_for, session
from etl.get_schedule import Schedule
from etl.utils import df_to_tuples
from forms import AccessCodeForm
import datetime as dt
import pandas as pd
import numpy as np

app = Flask(__name__)
app.config["SECRET_KEY"] = "tylers-secret-key"


@app.route("/", methods=["GET", "POST"])
def homepage():
    form = AccessCodeForm()
    if form.is_submitted():
        session["accesscode"] = request.form.get("accesscode")
        return redirect(url_for("filter"))
    return render_template("home.html", form=form)


@app.route("/filter", methods=["GET", "POST"])
def filter():
    login_code = session.get("accesscode", None)

    # Set defaults
    start_date = dt.date.today().strftime("%Y-%m-%d")
    end_date = (dt.date.today() + dt.timedelta(14)).strftime("%Y-%m-%d")
    name_options = Schedule().get_unique_names(
        login_code=login_code,
        start_date=start_date,
        end_date=end_date,
    )

    if request.method == "POST":
        session["start_date"] = request.form["start_date"]
        session["end_date"] = request.form["end_date"]
        session["selected_names"] = request.form.getlist("names")
        return redirect(url_for("availability"))

    return render_template(
        "filter.html",
        start_date=start_date,
        end_date=end_date,
        name_options=name_options,
    )


@app.route("/availability", methods=["GET", "POST"])
def availability():
    login_code = session.get("accesscode", None)
    start_date = session.get("start_date", None)
    end_date = session.get("end_date", None)
    names = session.get("selected_names", None)

    # Filter data and pass as args into html
    free_time = Schedule().run(
        login_code=login_code,
        start_date=start_date,
        end_date=end_date,
        names=names,
    )

    # Format table data for HTML to parse
    headings, free_time_data = df_to_tuples(free_time)
    names_str = ", ".join(names)
    return render_template(
        "availability.html",
        headings=headings,
        free_time_data=free_time_data,
        names=names_str,
        start_date=start_date,
        end_date=end_date,
    )


@app.route("/hourly_availability")
def hourly_availability():
    # TODO: Generate free time into a JSON like this
    availabilities = {
        "July 10": [
            {"start_time": 0, "end_time": 6, "display_range": "12:00AM - 6:00AM"},
            {"start_time": 17, "end_time": 24, "display_range": "5:00PM - 11:59PM"},
        ],
        "July 11": [
            {"start_time": 6, "end_time": 24, "display_range": "6:00PM - 11:59PM"},
        ],
        "July 14": [
            {"start_time": 9, "end_time": 24, "display_range": "9:00PM - 11:59PM"},
        ],
    }
    hours = list(np.arange(24))
    return render_template(
        "hourly_availability.html",
        availabilities=availabilities,
        hours=hours,
    )
