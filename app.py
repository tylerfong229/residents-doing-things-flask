from flask import Flask, render_template, request, redirect, url_for, session
from etl.get_schedule import Schedule
from etl.utils import df_to_tuples
from forms import AccessCodeForm, CreateNameDropDown
import datetime as dt
from flask_wtf import FlaskForm

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

    form = CreateNameDropDown(name_options)
    if form.validate_on_submit():
        session["start_date"] = request.form["start_date"]
        session["end_date"] = request.form["end_date"]
        session["names"] = form.names.data
        return redirect(url_for("availability"))

    return render_template(
        "filter.html",
        form=form,
        start_date=start_date,
        end_date=end_date,
    )


@app.route("/availability", methods=["GET", "POST"])
def availability():
    login_code = session.get("accesscode", None)
    start_date = session.get("start_date", None)
    end_date = session.get("end_date", None)
    names = session.get("names", None)

    # Filter data and pass as args into html
    free_time = Schedule().run(
        login_code=login_code,
        start_date=start_date,
        end_date=end_date,
        names=names,
    )

    # Format table data for HTML to parse
    headings, free_time_data = df_to_tuples(free_time)

    return render_template(
        "availability.html",
        headings=headings,
        free_time_data=free_time_data,
        names=", ".join(names),
        start_date=start_date,
        end_date=end_date,
    )
