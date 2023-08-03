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
    end_date = (dt.date.today() + dt.timedelta(60)).strftime("%Y-%m-%d")
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
    availabilities = Schedule().run(
        login_code=login_code,
        start_date=start_date,
        end_date=end_date,
        names=names,
    )
    print(names)
    return render_template(
        "hourly_availability.html",
        availabilities=availabilities,
        hours=list(np.arange(24)),
        names=names,
        start_date=dt.datetime.strptime(start_date, "%Y-%m-%d").strftime("%B %-d"),
        end_date=dt.datetime.strptime(end_date, "%Y-%m-%d").strftime("%B %-d"),
    )
