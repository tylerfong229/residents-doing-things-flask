import pandas as pd
import requests
import datetime as dt
import csv
import os


def request_amion(
    login_code: str,
    return_dataframe: bool = False,
    start_year: int = 0,
    start_month: int = 0,
    start_day: int = 0,
    days: int = 0,
):
    url_prefix = "http://www.amion.com/cgi-bin/ocs?"
    url = f"{url_prefix}Lo={login_code}&Rpt=619"
    if start_year != 0:
        url = (
            url
            + f"&Day={str(start_day)}&Month={str(start_month)}&Year={str(start_year)}&Days={str(days)}"
        )
    print(f"url: {url}")
    response = requests.get(url=url, headers={"Connection": "close"})

    if return_dataframe:
        raw_schedule_list = response.text.split("\n")[6:]

        schedule_cols = [
            "name",
            "name_id1",
            "name_id2",
            "team",
            "team_id1",
            "team_id2",
            "date",
            "start_time",
            "end_time",
        ]

        df_list = []
        for row in csv.reader(raw_schedule_list, delimiter=","):
            if len(row) > 0:
                df_list.append(row)
        schedule_df = pd.DataFrame(df_list, columns=schedule_cols)
        print("Raw Schedule DF:")
        print(schedule_df)
        print(f"requested schedule from API row count: {schedule_df.shape[0]}")
        return schedule_df

    return response


def parse_dates(start_date: str, end_date: str):
    """Converts input dates into usable data for API"""
    start_date_dt = dt.datetime.strptime(start_date, "%Y-%m-%d")
    end_date_dt = dt.datetime.strptime(end_date, "%Y-%m-%d")

    syear = start_date_dt.year
    smonth = start_date_dt.month
    sday = start_date_dt.day
    days = (end_date_dt - start_date_dt).days

    if days < 0:
        # TODO: Need to do error handling
        pass

    return {
        "start_year": syear,
        "start_month": smonth,
        "start_day": sday,
        "days": days,
        "start_date": start_date_dt,
        "end_date": end_date_dt,
    }


def validate_login_code(login_code: str):
    response = request_amion(login_code=login_code)
    return "bad password" not in response.text.lower()


def get_unique_names(login_code: str):
    response_df = request_amion(login_code=login_code, return_dataframe=True)
    names = list(response_df.name.sort_values().unique())
    return names


def get_cache_path(
    start_year: int,
    start_month: int,
    start_day: int,
    days: int,
):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prev_dir = "/".join(current_dir.split("/")[:-1])
    cache_prefix = f"{prev_dir}/_cache"
    cache_path = (
        f"{cache_prefix}/amion_cache_start={start_year}{start_month}{start_day}_days={days}.csv"
    )
    print(cache_path)
    return cache_path
