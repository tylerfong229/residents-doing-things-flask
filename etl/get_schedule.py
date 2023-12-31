import pandas as pd

import datetime as dt
from etl.utils import parse_dates, get_schedule
from defaults.constants import Constants


class Schedule:
    def find_availability(
        self,
        login_code: str,
        start_date: str,
        end_date: str,
        names: list,
        start_time: str = "0",
        end_time: str = "24",
    ):
        """Controller method to be called by model"""
        # Handle no names selected
        if len(names) == 0:
            json_freetime = {"ERROR: NO NAMES SELECTED": ""}
            final_relevant_names = []
            return json_freetime, final_relevant_names

        # Find availability if names selected
        parsed_dates = parse_dates(start_date=start_date, end_date=end_date)
        raw_schedule = get_schedule(
            login_code=login_code,
            start_year=parsed_dates["start_year"],
            start_month=parsed_dates["start_month"],
            start_day=parsed_dates["start_day"],
            days=parsed_dates["days"],
        )
        cleaned_schedule = self.clean_schedule(schedule=raw_schedule, names=names)
        freetime, final_relevant_names = self.find_free_time(
            schedule=cleaned_schedule,
            start_year=parsed_dates["start_year"],
            start_month=parsed_dates["start_month"],
            start_day=parsed_dates["start_day"],
            days=parsed_dates["days"],
            relevant_names=names,
            start_time=int(start_time),
            end_time=int(end_time),
        )
        formatted_freetime = self.format_free_time(freetime=freetime)
        json_freetime = self.freetime_to_json(formatted_freetime)
        return json_freetime, final_relevant_names

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

        schedule_no_ids = schedule[
            (schedule["grouping"].isin(["On Call", "Clinic"]))
            & (schedule["staff_type"].isin(Constants().allowed_staff_types))
        ][["name", "team", "date", "start_time", "end_time"]].copy()
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
        schedule_no_ids = schedule_no_ids[["name", "team", "start_time", "end_time"]]
        return schedule_no_ids

    def find_free_time(
        self,
        schedule: pd.DataFrame,
        start_year: int,
        start_month: int,
        start_day: int,
        days: int,
        relevant_names: list,
        start_time: int,
        end_time: int,
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

        # If schedule is empty for selected dates then all times are free
        if schedule.shape[0] == 0:
            working_hours = pd.DataFrame({"working_hour": []})
        else:
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
                updated_name = f"{name}*"
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

        # Cleanup
        work_nonwork["timestamp"] = work_nonwork["date"]
        work_nonwork["hour"] = (
            work_nonwork["date"].dt.strftime("%H:%M").str.split(":").str[0].astype(int)
        )
        work_nonwork["date"] = work_nonwork["date"].dt.date

        # Apply filter selected on start and end time to look for:
        work_nonwork.loc[
            (
                ((work_nonwork["hour"] < start_time) | (work_nonwork["hour"] > end_time))
                & (work_nonwork["working_ct"] == 0)
            ),
            "working_ct",
        ] = 1

        # Tag rows
        free_condition = work_nonwork["working_ct"] == 0
        work_nonwork["free_time"] = False
        work_nonwork.loc[free_condition, "free_time"] = True

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
                            "start_time": [int(round(hour_start))],
                            "end_time": [int(round(hour_end))],
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
        freetime["date"] = pd.to_datetime(freetime["date"]).dt.strftime("%b %-d (%a)")
        for row in freetime.iterrows():
            r = row[1]
            if r["end_time"] == 23:
                r["end_time"] = 24
            hours = int(r["end_time"] - r["start_time"])
            free_time_detail = {
                "start_time": r["start_time"],
                "end_time": r["end_time"],
                "display_time_range": f"{r['time_period']}",
                "display_hour_range": f"({str(hours)} hours)",
            }
            if r["date"] != prev_date:
                availabilities[r["date"]] = [free_time_detail]
                prev_date = r["date"]
            else:
                availabilities[r["date"]].append(free_time_detail)
                prev_date = r["date"]
        print("\nAvailabilities:")
        print(availabilities)
        return availabilities
