import datetime
import urllib.parse

import pandas as pd
import pytz

from valencianow import config

logger = config.logger

TB_NOW_PIPE = "now_pipe"
TB_HIST_PIPE = "hist_pipe"
TB_HIST_MEAS = "hist_meas"
TB_HIST_Y = "hist_y"
TB_PER_DAY_PIPE = "per_day_pipe"
TB_PER_DAY_Y = "per_day_y"
TB_PER_DOW_PIPE = "per_dow_pipe"
TB_PER_DOW_Y = "per_dow_y"
TB_SENSOR_PARAM = "sensor_param"
TB_SENSOR_COL = "sensor_col"
TB_DATETIME_COL = "datetime_col"

COL_DATETIME = "datetime"
COL_DATE = "date"
COL_LAT = "lat"
COL_LON = "lon"
COL_DAY = "day"
COL_SENSOR = "sensor"

# the names of the Tinybird pipes
TB_PIPES = {
    config.TAB_AIR: {
        TB_NOW_PIPE: "air_now",
        TB_HIST_PIPE: "air_history",
        TB_HIST_MEAS: "air quality",
        TB_HIST_Y: "ica",
        TB_PER_DAY_PIPE: "air_per_day",
        TB_PER_DAY_Y: "avg_ica",
        TB_PER_DOW_PIPE: "air_per_day_of_week",
        TB_PER_DOW_Y: "avg_ica",
        TB_SENSOR_PARAM: "_objectid",
        TB_SENSOR_COL: "_objectid",
        TB_DATETIME_COL: "fecha_carga",
    },
    config.TAB_CAR: {
        TB_NOW_PIPE: "cars_now",
        TB_HIST_PIPE: "cars_history",
        TB_HIST_MEAS: "cars per hour",
        TB_HIST_Y: "ih",
        TB_PER_DAY_PIPE: "cars_per_day",
        TB_PER_DAY_Y: "avg_ih",
        TB_PER_DOW_PIPE: "cars_per_day_of_week",
        TB_PER_DOW_Y: "avg_ih",
        TB_SENSOR_PARAM: "idpm",
        TB_SENSOR_COL: "idpm",
        TB_DATETIME_COL: "last_edited_date",
    },
    config.TAB_BIKE: {
        TB_NOW_PIPE: "bikes_now",
        TB_HIST_PIPE: "bikes_history",
        TB_HIST_MEAS: "bikes per hour",
        TB_HIST_Y: "ih",
        TB_PER_DAY_PIPE: "bikes_per_day",
        TB_PER_DAY_Y: "avg_ih",
        TB_PER_DOW_PIPE: "bikes_per_day_of_week",
        TB_PER_DOW_Y: "avg_ih",
        TB_SENSOR_PARAM: "idpm",
        TB_SENSOR_COL: "idpm",
        TB_DATETIME_COL: "last_edited_date",
    },
}


def _process(df: pd.DataFrame) -> pd.DataFrame | None:
    if df.shape[0] > 0:
        # normalize column names from Tinybird endpoints
        if "geo_point_2d" in df.columns:
            # convert geo_point_2d to lat and lon
            df[[COL_LAT, COL_LON]] = df["geo_point_2d"].str.split(",", expand=True)
            df[COL_LAT] = pd.to_numeric(df[COL_LAT])
            df[COL_LON] = pd.to_numeric(df[COL_LON])
            df = df.drop(columns=["geo_point_2d"])
        # normalize sensor column names
        if "idpm" in df.columns:
            df[COL_SENSOR] = df["idpm"]
            df = df.drop(columns=["idpm"])
        if "_objectid" in df.columns:
            df[COL_SENSOR] = df["_objectid"]
            df = df.drop(columns=["_objectid"])
        # normalize datetime column names
        if "last_edited_date" in df.columns:
            df[COL_DATETIME] = pd.to_datetime(df["last_edited_date"])
            df[COL_DATE] = df["last_edited_date"]
            df = df.drop(columns=["last_edited_date"])
        if "fecha_carga" in df.columns:
            df[COL_DATETIME] = pd.to_datetime(df["fecha_carga"])
            df[COL_DATE] = df["fecha_carga"]
            df = df.drop(columns=["fecha_carga"])
        # parse date columns
        if COL_DAY in df.columns:
            df[COL_DAY] = pd.to_datetime(df[COL_DAY])
        if COL_DATETIME in df.columns:
            is_datetime = pd.api.types.is_datetime64_any_dtype(df[COL_DATETIME])
            if not is_datetime:
                df[COL_DATETIME] = pd.to_datetime(df[COL_DATETIME])
            # add one hour to correct timezone offset
            df[COL_DATETIME] = df[COL_DATETIME] + pd.Timedelta(hours=1)
            # update COL_DATE to reflect the adjusted datetime
            if COL_DATE in df.columns:
                df[COL_DATE] = df[COL_DATETIME].dt.strftime("%Y-%m-%d %H:%M:%S")
        return df
    return None


def _date_to_utc(date: str) -> str:
    # receive a data with format YYYY-MM-DD HH:MM:SS in timezone
    # Europe/Madrid and return a date with the same format but in timezone UTC
    madrid_tz = pytz.timezone("Europe/Madrid")
    utc_tz = pytz.utc
    naive_datetime = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    localized_datetime = madrid_tz.localize(naive_datetime)
    utc_datetime = localized_datetime.astimezone(utc_tz)
    return utc_datetime.strftime("%Y-%m-%d %H:%M:%S")


def _min_date(current_date: datetime.datetime, timespan: str) -> str:
    output = current_date
    if timespan == "Today":
        output -= datetime.timedelta(days=1)
    elif timespan == "Last Week":
        output -= datetime.timedelta(days=7)
    elif timespan == "Last Month":
        output -= datetime.timedelta(days=31)
    elif timespan == "Last Year":
        output -= datetime.timedelta(days=365)
    return output.strftime("%Y-%m-%d %H:%M:%S")


def load_data(
    pipe_name: str,  # the name of the Tinybird pipe
    filter_max_date: str | None,
    filter_sensor: int | None = None,
    filter_timespan: str | None = None,
    local_time: bool = False,
    sensor_param: str = "idpm",  # parameter name for sensor filter
) -> pd.DataFrame | None:
    """Load data from the given Tinybird pipe name.

    Some optional filters can be provided.
    A None value can be returned if there are no rows.
    """
    params: dict = {}
    if filter_max_date:
        if not local_time:
            filter_max_date = _date_to_utc(filter_max_date)
        params["max_date"] = filter_max_date
    if filter_timespan:
        if filter_max_date:
            max_date = datetime.datetime.strptime(filter_max_date, "%Y-%m-%d %H:%M:%S")
        else:
            max_date = datetime.datetime.now(datetime.timezone.utc)
        params["min_date"] = _min_date(max_date, filter_timespan)
    if filter_sensor:
        params[sensor_param] = filter_sensor
    logger.info(f"Retrieving {pipe_name} data from Tinybird with params: {params}")
    params["token"] = config.TINYBIRD_TOKEN
    url = f"{config.TINYBIRD_API}/v0/pipes/{pipe_name}.csv?{urllib.parse.urlencode(params)}"
    logger.info(f"Retrieving from Tinybird url {url}")
    return _process(pd.read_csv(url))
