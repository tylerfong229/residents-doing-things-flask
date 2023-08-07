import pandas as pd
import requests
import csv
from typing import Tuple
import datetime as dt
import os


class Schedule:
    def __init__(self):
        pass

    def run(
        self,
        login_code: str,
        start_date: str,
        end_date: str,
        names: list,
    ):
        """Controller method to be called by model"""
        if len(names) == 0:
            return pd.DataFrame({"name": ["None Selected"]})

        parsed_dates = self.parse_dates(start_date=start_date, end_date=end_date)
        print("Getting raw_schedule...")
        raw_schedule = self.get_raw_schedule(
            login_code=login_code,
            start_year=parsed_dates["start_year"],
            start_month=parsed_dates["start_month"],
            start_day=parsed_dates["start_day"],
            days=parsed_dates["days"],
        )
        print(f"raw_schedule length: {raw_schedule.shape[0]}.  Below are the first 10 rows:")
        print(raw_schedule.head(10))
        print("Cleaning schedule...")
        cleaned_schedule = self.clean_schedule(schedule=raw_schedule, names=names)
        print(
            f"cleaned_schedule length: {cleaned_schedule.shape[0]}.  Below are the first 10 rows:"
        )
        print(cleaned_schedule.head(10))

        print("Finding freetime...")
        freetime, final_relevant_names = self.find_free_time(
            schedule=cleaned_schedule,
            start_year=parsed_dates["start_year"],
            start_month=parsed_dates["start_month"],
            start_day=parsed_dates["start_day"],
            days=parsed_dates["days"],
            relevant_names=names,
        )
        print(f"freetime length: {freetime.shape[0]}.  Below are the first 10 rows:")
        print(freetime.head(10))

        print("Formatting freetime...")
        formatted_freetime = self.format_free_time(freetime=freetime)
        json_freetime = self.freetime_to_json(formatted_freetime)
        return json_freetime, final_relevant_names

    def get_unique_names(
        self,
        login_code: str,
        start_date: str,
        end_date: str,
    ):
        parsed_dates = self.parse_dates(start_date=start_date, end_date=end_date)

        raw_schedule = self.get_raw_schedule(
            login_code=login_code,
            start_year=parsed_dates["start_year"],
            start_month=parsed_dates["start_month"],
            start_day=parsed_dates["start_day"],
            days=parsed_dates["days"],
        )
        names = list(raw_schedule.name.sort_values().unique())
        return names

    def parse_dates(self, start_date, end_date):
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

    def get_raw_schedule(
        self,
        login_code: str,
        start_year: int,
        start_month: int,
        start_day: int,
        days: int,
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
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prev_dir = "/".join(current_dir.split("/")[:-1])
        cache_prefix = f"{prev_dir}/_cache"
        cache_path = f"{cache_prefix}/amion_cache_start={start_year}{start_month}{start_day}_days={days}.csv"
        print(cache_path)
        if os.path.isfile(cache_path):
            print("reading from cache")
            return pd.read_csv(cache_path)

        url_prefix = "http://www.amion.com/cgi-bin/ocs?"
        url = f"{url_prefix}Lo={login_code}&Rpt=619&Day={str(start_day)}&Month={str(start_month)}&Year={str(start_year)}&Days={str(days)}"
        response = requests.get(url)
        raw_schedule_list = response.text.split("\n")[6:]
        print("raw_schedule:")
        print(raw_schedule_list)

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
        print(f"requested schedule from API row count: {schedule_df.shape[0]}")
        outfile = open(cache_path, "wb")
        schedule_df.to_csv(outfile)
        outfile.close()
        return schedule_df

    def clean_schedule(self, schedule: pd.DataFrame, names: list) -> pd.DataFrame:
        """
        Cleans raw schedule from amion api
            - Handles double rows for multiple teams
            - Handles 24 hour shifts

        Args:
            schedule: Dataframe of raw schedule from Amion API

        Returns:
            Schedule dataframe cleaned and formatted
        """

        schedule_no_ids = schedule[["name", "team", "date", "start_time", "end_time"]].copy()
        if len(names) > 0:
            schedule_no_ids = schedule_no_ids[schedule_no_ids["name"].isin(names)]
        schedule_no_ids["date"] = pd.to_datetime(schedule_no_ids["date"], format="%m-%d-%y")

        # Handling weirdness in the data:
        # If you are team 4/5, it can show as 2 lines
        schedule_no_ids["team"] = schedule_no_ids.groupby(
            ["name", "date", "start_time", "end_time"]
        )["team"].transform(lambda x: ", ".join(x))
        schedule_no_ids = schedule_no_ids.drop_duplicates()

        for time_col in ["start_time", "end_time"]:
            schedule_no_ids.loc[schedule_no_ids[time_col].astype(str) == "0", time_col] = "000"
            schedule_no_ids[time_col] = schedule_no_ids[time_col].astype(str)
            schedule_no_ids[time_col] = (
                schedule_no_ids[time_col].str[:-2] + ":" + schedule_no_ids[time_col].str[-2:]
            )
            schedule_no_ids[time_col] = (
                schedule_no_ids["date"].dt.date.astype(str) + " " + schedule_no_ids[time_col]
            )
            schedule_no_ids[time_col] = pd.to_datetime(
                schedule_no_ids[time_col], format="%Y-%m-%d %H:%M"
            )

        # If start_time and end_time are the same, it's because its a 24 hr shift
        # If start time is later in the day then end time, then it's a night shift
        schedule_no_ids.loc[
            schedule_no_ids["start_time"] >= schedule_no_ids["end_time"], "end_time"
        ] = schedule_no_ids["end_time"] + dt.timedelta(days=1)

        return schedule_no_ids[["name", "team", "start_time", "end_time"]]

    def find_free_time(
        self,
        schedule: pd.DataFrame,
        start_year: int,
        start_month: int,
        start_day: int,
        days: int,
        relevant_names: list,
    ) -> pd.DataFrame:
        """Identifies which hours people are working and not working"""

        # Get every hour between start and end date
        scope = pd.DataFrame(
            pd.date_range(
                start=f"{str(start_year)}-{str(start_month)}-{str(start_day)}",
                periods=int(days) * 24,
                freq="1H",
            ),
            columns=["date"],
        )

        # Find which hours are busy or free for each name
        # TODO: handle cases where name is not in schedule
        #       could mean theyre on vacation or that scheduler hasn't input their schedule
        #       - Assumption should be that they are free the whole time (note assumption in output)
        working_hours = schedule.copy()
        working_hours["start_time"] = pd.to_datetime(working_hours["start_time"])
        working_hours["end_time"] = pd.to_datetime(working_hours["end_time"])
        working_hours["hour"] = working_hours.apply(
            lambda row: pd.date_range(row["start_time"], row["end_time"], freq="H"), axis=1
        )

        working_hours = (
            working_hours.explode("hour")
            .reset_index()
            .drop(columns=["start_time", "end_time"])
            .rename(columns={"hour": "working_hour"})
            .set_index("working_hour")
            .reset_index()[["name", "working_hour"]]
            .assign(working=1)
            .pivot_table(index="working_hour", columns="name", values="working")
            .reset_index()
        )
        final_relevant_names = []
        for name in relevant_names:
            if name not in working_hours.columns:
                updated_name = f"{name} (No working hours in schedule during date range)"
                working_hours[updated_name] = 0
                final_relevant_names.append(updated_name)
            else:
                final_relevant_names.append(name)

        work_nonwork = scope.merge(
            working_hours,
            how="left",
            left_on="date",
            right_on="working_hour",
        ).fillna(0)

        for name in final_relevant_names:
            if "working_ct" not in work_nonwork.columns:
                work_nonwork["working_ct"] = work_nonwork[name]
            else:
                work_nonwork["working_ct"] += work_nonwork[name]

        # Tag rows
        free_condition = work_nonwork["working_ct"] == 0
        work_nonwork["free_time"] = False
        work_nonwork.loc[free_condition, "free_time"] = True

        # Cleanup
        work_nonwork["timestamp"] = work_nonwork["date"]
        work_nonwork["hour"] = (
            work_nonwork["date"].dt.strftime("%H:%M").str.split(":").str[0].astype(int)
        )
        work_nonwork["date"] = work_nonwork["date"].dt.date

        return (
            work_nonwork[["timestamp", "date", "hour"] + final_relevant_names + ["free_time"]],
            final_relevant_names,
        )

    def format_free_time(self, freetime: pd.DataFrame):
        """Formats dataframe for display on site"""
        # TODO: add # of hours next to free time blocks

        freetime.loc[freetime["hour"] == 23, "timestamp"] = freetime["timestamp"] + pd.Timedelta(
            minutes=59
        )
        freetime["timestamp"] = freetime["timestamp"].dt.strftime("%-I:%M %p")
        freetime = freetime.reset_index()
        freetime_fwd = freetime.copy()
        freetime_fwd["index"] = freetime_fwd["index"] + 1

        ft = freetime.merge(
            freetime_fwd[["index", "date", "free_time"]],
            on="index",
            how="left",
            suffixes=["", "_1hr_fwd"],
        )

        ft = ft.loc[
            (ft["date_1hr_fwd"].isnull())
            | ((ft["date"] == ft["date_1hr_fwd"]) & (ft["free_time"] != ft["free_time_1hr_fwd"]))
            | ((ft["hour"] == 23) & (ft["free_time"] == ft["free_time_1hr_fwd"]))
            | (ft["hour"] == 0)
        ][["timestamp", "date", "hour", "free_time"]]

        ct = 0
        list_of_display_rows = []
        for row in ft.to_dict("records"):
            if ct == 0 or row["hour"] == 0:
                time_start = str(row["timestamp"])
                free_at_start = row["free_time"]
                hour_start = row["hour"]
                time_end = ""
                ct += 1
            elif time_end == "":
                time_end = str(row["timestamp"])
                free_at_end = row["free_time"]
                hour_end = row["hour"]

                if free_at_start:
                    status = "FREE"
                else:
                    status = "BUSY"

                list_of_display_rows.append(
                    pd.DataFrame(
                        {
                            "status": [status],
                            "date": [str(row["date"])],
                            "start_time": [int(hour_start)],
                            "end_time": [int(hour_end)],
                            "time_period": [f"{time_start} to {time_end}"],
                        }
                    )
                )

                free_at_start = free_at_end
                time_start = time_end
                hour_start = hour_end
                time_end = ""
                ct += 1

        display_df = pd.concat(list_of_display_rows)

        return display_df[display_df["status"] == "FREE"].drop(columns="status")

    def freetime_to_json(self, freetime: pd.DataFrame) -> dict:
        availabilities = {}
        prev_date = ""
        freetime = freetime.sort_values(by="date")
        freetime["date"] = pd.to_datetime(freetime["date"]).dt.strftime("%B %-d (%A)")
        for row in freetime.iterrows():
            r = row[1]
            hours = int(r["end_time"] - r["start_time"])
            free_time_detail = {
                "start_time": r["start_time"],
                "end_time": r["end_time"],
                "display_range": f"{r['time_period']} ({str(hours)} hours)",
            }
            if r["date"] != prev_date:
                availabilities[r["date"]] = [free_time_detail]
                prev_date = r["date"]
            else:
                availabilities[r["date"]].append(free_time_detail)
                prev_date = r["date"]

        return availabilities
