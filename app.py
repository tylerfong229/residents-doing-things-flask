from flask import Flask, render_template, request, redirect, url_for, session
from etl.get_schedule import Schedule
from etl.utils import validate_login_code, get_unique_names
from forms import AccessCodeForm
import datetime as dt
import numpy as np
from defaults.constants import Constants

app = Flask(__name__)
app.config["SECRET_KEY"] = "tylers-secret-key"
print("\n========== NEW SESSION ==========")


@app.route("/", methods=["GET", "POST"])
def homepage():
    form = AccessCodeForm()
    error_message = ""
    if form.is_submitted():
        access_code = request.form.get("accesscode").lower()
        session["access_code"] = access_code
        print(f"ACCESS_CODE: {access_code}")
        if validate_login_code(login_code=access_code):
            return redirect(url_for("filter", access_code=access_code, staff_type="All"))
        error_message = f"The access code {access_code} is not a valid Amion Access Code"

    return render_template("home.html", form=form, error_message=error_message)


@app.route("/filter/access_code=<access_code>&staff_type=<staff_type>", methods=["GET", "POST"])
def filter(access_code, staff_type):
    # Set defaults
    start_date = dt.date.today().strftime("%Y-%m-%d")
    end_date = (dt.date.today() + dt.timedelta(14)).strftime("%Y-%m-%d")
    name_options = get_unique_names(
        login_code=access_code,
        start_date=start_date,
        end_date=(dt.date.today() + dt.timedelta(90)).strftime("%Y-%m-%d"),
        staff_types=staff_type,
    )
    name_err_message = ""
    date_err_message = ""
    err_ct = 0

    if request.method == "POST":
        if request.form["submit_button"] == "Refresh":
            selected_staff_type = request.form.getlist("staff_types")[0]
            return redirect(
                url_for(
                    "filter",
                    access_code=access_code,
                    staff_type=selected_staff_type,
                )
            )
        else:
            start_date = request.form["start_date"]
            start_date_dt = dt.datetime.strptime(start_date, "%Y-%m-%d")
            end_date = request.form["end_date"]
            end_date_dt = dt.datetime.strptime(end_date, "%Y-%m-%d")
            names = request.form.getlist("names")
            session["start_date"] = start_date
            session["end_date"] = end_date
            session["selected_names"] = names
            print(f"start_date: {start_date}")
            print(f"end_date: {end_date}")
            print(f"selected_names: {names}")
            if start_date_dt >= end_date_dt:
                date_err_message = "Start date must be before end date"
                err_ct += 1
            if len(names) == 0:
                name_err_message = "Please select at least 1 person"
                err_ct += 1
            if err_ct == 0:
                selected_names_str = "&".join(names).replace(",", "").replace(" ", "")
                return redirect(
                    url_for(
                        "availability",
                        access_code=access_code,
                        start_date=start_date,
                        end_date=end_date,
                        selected_names_str=selected_names_str,
                    )
                )

    return render_template(
        "filter.html",
        start_date=start_date,
        end_date=end_date,
        name_options=name_options,
        date_err_message=date_err_message,
        name_err_message=name_err_message,
        staff_type=staff_type,
        possible_staff_types=Constants().allowed_staff_types,
    )


@app.route(
    "/availability/access_code=<access_code>&start_date=<start_date>&end_date=<end_date>&names=<selected_names_str>",
    methods=["GET", "POST"],
)
def availability(access_code, start_date, end_date, selected_names_str):
    names = session.get("selected_names", None)
    start_time = 0
    end_time = 24

    if request.method == "POST":
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]

    # Filter data and pass as args into html
    availabilities, final_relevant_names = Schedule().find_availability(
        login_code=access_code,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        names=names,
    )

    if len(availabilities) == 0:
        return redirect(url_for("no_freetime", access_code=access_code))

    return render_template(
        "hourly_availability.html",
        access_code=access_code,
        availabilities=availabilities,
        hours=list(np.arange(24)),
        names=final_relevant_names,
        start_date=dt.datetime.strptime(start_date, "%Y-%m-%d").strftime("%B %-d"),
        end_date=dt.datetime.strptime(end_date, "%Y-%m-%d").strftime("%B %-d"),
        possible_hours=Constants().possible_hours,
        start_time=int(start_time),
        end_time=int(end_time),
    )


@app.route("/no_freetime/access_code=<access_code>", methods=["GET", "POST"])
def no_freetime(access_code):
    return render_template("no_freetime.html", access_code=access_code)
