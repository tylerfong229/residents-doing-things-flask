from flask import Flask, render_template, request, redirect, url_for, session
from etl.get_schedule import Schedule
from etl.utils import validate_login_code, get_unique_names
from forms import AccessCodeForm
import datetime as dt
import numpy as np
from utils.constants import Constants

app = Flask(__name__)
app.config["SECRET_KEY"] = "tylers-secret-key"
print("\n========== NEW SESSION ==========")


@app.route("/", methods=["GET", "POST"])
def homepage():
    form = AccessCodeForm()
    error_message = ""
    if form.is_submitted():
        login_code = request.form.get("accesscode").lower()
        print(f"LOGIN_CODE: {login_code}")
        session["accesscode"] = login_code
        if validate_login_code(login_code=login_code):
            return redirect(url_for("filter"))
        error_message = f"The access code {login_code} is not a valid Amion Access Code"

    return render_template("home.html", form=form, error_message=error_message)


@app.route("/filter", methods=["GET", "POST"])
def filter():
    login_code = session.get("accesscode", None)

    # Set defaults
    start_date = dt.date.today().strftime("%Y-%m-%d")
    name_options = get_unique_names(login_code=login_code)

    if request.method == "POST":
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        names = request.form.getlist("names")
        session["start_date"] = start_date
        session["end_date"] = end_date
        session["selected_names"] = names
        print(f"start_date: {start_date}")
        print(f"end_date: {end_date}")
        print(f"selected_names: {names}")

        return redirect(url_for("availability"))

    return render_template(
        "filter.html",
        start_date=start_date,
        end_date=(dt.date.today() + dt.timedelta(14)).strftime("%Y-%m-%d"),
        name_options=name_options,
    )


@app.route("/availability", methods=["GET", "POST"])
def availability():
    login_code = session.get("accesscode", None)
    start_date = session.get("start_date", None)
    end_date = session.get("end_date", None)
    names = session.get("selected_names", None)
    start_time = 0
    end_time = 24

    if request.method == "POST":
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]

    # Filter data and pass as args into html
    availabilities, final_relevant_names = Schedule().find_availability(
        login_code=login_code,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        names=names,
    )

    if len(availabilities) == 0:
        return redirect(url_for("no_freetime"))

    return render_template(
        "hourly_availability.html",
        availabilities=availabilities,
        hours=list(np.arange(24)),
        names=final_relevant_names,
        start_date=dt.datetime.strptime(start_date, "%Y-%m-%d").strftime("%B %-d"),
        end_date=dt.datetime.strptime(end_date, "%Y-%m-%d").strftime("%B %-d"),
        possible_hours=Constants().possible_hours,
    )


@app.route("/no_freetime", methods=["GET", "POST"])
def no_freetime():
    return render_template("no_freetime.html")


@app.route("/no_names_selected", methods=["GET", "POST"])
def no_names_selected():
    return render_template("no_names_selected.html")
