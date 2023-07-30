from flask import Flask, render_template, request, redirect, url_for, session
from etl.get_schedule import Schedule
from etl.utils import df_to_tuples
from forms import AccessCodeForm
import datetime as dt

app = Flask(__name__)
app.config["SECRET_KEY"] = "tylers-secret-key"


@app.route("/", methods=["GET", "POST"])
def homepage():
    form = AccessCodeForm()
    if form.is_submitted():
        session["accesscode"] = request.form.get("accesscode")
        # return scope()
        return redirect(url_for("availability"))
    return render_template("home.html", form=form)


@app.route("/availability", methods=["GET", "POST"])
def availability():
    login_code = session.get("accesscode", None)
    # Set defaults
    start_date = dt.date.today().strftime("%Y-%m-%d")
    end_date = (dt.date.today() + dt.timedelta(14)).strftime("%Y-%m-%d")
    names = ["Benedetto, Lauren", "Freeburg, Taylor"]

    # If POST, replace defaults with user input values
    if request.method == "POST":
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        print(start_date, end_date)

    # Filter data and pass as args into html
    free_time = Schedule().run(
        login_code=login_code,
        start_date=start_date,
        end_date=end_date,
        names=names,
    )

    # return_df = schedule_df[["name", "team"]]
    headings, data = df_to_tuples(free_time)

    return render_template(
        "availability.html",
        headings=headings,
        data=data,
        start_date=start_date,
        end_date=end_date,
    )
