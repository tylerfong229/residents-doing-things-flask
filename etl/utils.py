import pandas as pd
import requests
import datetime as dt
import csv
import os
from typing import Tuple
from defaults.constants import Constants


def request_amion(
    login_code: str,
    start_year: int = 0,
    start_month: int = 0,
    start_day: int = 0,
    days: int = 0,
    return_dataframe: bool = True,
):
    url_prefix = "http://www.amion.com/cgi-bin/ocs?"
    url = f"{url_prefix}Lo={login_code}&Rpt=625c"
    if start_year != 0:
        url = (
            url
            + f"&Day={str(start_day)}&Month={str(start_month)}&Year={str(start_year)}&Days={str(days)}"
        )
    print(f"url: {url}")
    response = requests.get(url=url, headers={"Connection": "close"})

    if return_dataframe:
        raw_schedule_list = response.text.split("\n")[7:]

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
            "staff_type",
            "pager_number",
            "tel_extension",
            "email",
            "col1",
            "col2",
            "col3",
            "grouping",
        ]

        df_list = []
        for row in csv.reader(raw_schedule_list, delimiter=","):
            if len(row) > 0:
                df_list.append(row)
        schedule_df = pd.DataFrame(df_list, columns=schedule_cols)
        print(f"requested schedule from API row count: {schedule_df.shape[0]}")

        return schedule_df[
            [
                "name",
                "team",
                "date",
                "staff_type",
                "start_time",
                "end_time",
                "grouping",
            ]
        ]

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
    response = request_amion(login_code=login_code, return_dataframe=False)
    return "bad password" not in response.text.lower()


def get_unique_names(login_code: str, start_date: str, end_date: str):
    parsed_dates = parse_dates(start_date=start_date, end_date=end_date)
    response_df = get_schedule(
        login_code=login_code,
        start_year=parsed_dates["start_year"],
        start_month=parsed_dates["start_month"],
        start_day=parsed_dates["start_day"],
        days=parsed_dates["days"],
    )
    names = list(
        response_df[response_df["staff_type"].isin(Constants().allowed_staff_types)]
        .name.sort_values()
        .unique()
    )
    return names


def get_cache_path(
    login_code: str,
    start_year: int,
    start_month: int,
    start_day: int,
    days: int,
):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prev_dir = "/".join(current_dir.split("/")[:-1])
    cache_prefix = f"{prev_dir}/_cache"
    cache_path = f"{cache_prefix}/login={login_code}_start={start_year}{start_month}{start_day}_days={days}.csv"
    print(cache_path)
    return cache_path


def get_schedule(
    login_code: str,
    start_year: int,
    start_month: int,
    start_day: int,
    days: int,
    return_dataframe: bool = True,
) -> Tuple[list, pd.DataFrame]:
    """
    Requests data from Amion API

    Args:
        login_code: amion login_code ex: "chla"
        start_year: Int of year to start query
        start_month: Int of month to start query
        start_day: Int of day to start query
        days: Int of number of days from from start to complete search

    Returns:
        Pandas dataframe of raw schedule
    """
    cache_path = get_cache_path(
        login_code=login_code,
        start_year=start_year,
        start_month=start_month,
        start_day=start_day,
        days=days,
    )
    if os.path.isfile(cache_path):
        print(f"reading from cache at {cache_path}")
        cache_df = pd.read_csv(cache_path)
        return cache_df

    schedule_df = request_amion(
        login_code=login_code,
        start_year=start_year,
        start_month=start_month,
        start_day=start_day,
        days=days,
        return_dataframe=return_dataframe,
    )
    print(f"schedule row count: {schedule_df.shape[0]}")
    # Write requested data to cache
    outfile = open(cache_path, "wb")
    schedule_df.to_csv(outfile)
    outfile.close()

    return schedule_df
