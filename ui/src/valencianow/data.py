import urllib.parse
from datetime import datetime

# Streamlit Cloud won't install the package, so we can't do:
# from valencianow import config
import config  # type: ignore
import pandas as pd
import pytz
import streamlit as st

logger = config.LOGGER

PIPES = {
    config.TAB_AIR: {
        "hist_pipe": "air_quality_history",
        "hist_meas": "air quality",
        "hist_y": "ica",
        "per_day_pipe": "air_quality_per_day",
        "per_day_y": "avg_ica",
        "per_dow_pipe": "air_quality_per_day_of_week",
        "per_dow_y": "avg_ica",
    },
    config.TAB_CAR: {
        "hist_pipe": "traffic_cars_history",
        "hist_meas": "cars per hour",
        "hist_y": "cars_per_hour",
        "per_day_pipe": "traffic_cars_per_day",
        "per_day_y": "avg_cars_per_hour",
        "per_dow_pipe": "traffic_cars_per_day_of_week",
        "per_dow_y": "avg_cars_per_hour",
    },
    config.TAB_BIKE: {
        "hist_pipe": "traffic_bikes_history",
        "hist_meas": "bikes per hour",
        "hist_y": "bikes_per_hour",
        "per_day_pipe": "traffic_bikes_per_day",
        "per_day_y": "avg_bikes_per_hour",
        "per_dow_pipe": "traffic_bikes_per_day_of_week",
        "per_dow_y": "avg_bikes_per_hour",
    },
}


def _process(df: pd.DataFrame) -> pd.DataFrame | None:
    # this function processes all the DataFrames used in valencianow
    if df.shape[0] > 0:
        if "point" in df.columns:
            # convert point in to lat and lon
            df[["lat", "lon"]] = df["point"].str.split(",", expand=True)
            df["lat"] = pd.to_numeric(df["lat"])
            df["lon"] = pd.to_numeric(df["lon"])
            df = df.drop(columns=["point"])
        # parse date columns
        if "day" in df.columns:
            df["day"] = pd.to_datetime(df["day"])
        if "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"])
        return df
    return None


def _date_to_utc(date: str) -> str:
    # receive a data with format YYYY-MM-DD HH:MM:SS in timezone
    # Europe/Madrid and return a date with the same format but in timezone UTC
    madrid_tz = pytz.timezone("Europe/Madrid")
    utc_tz = pytz.utc
    naive_datetime = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    localized_datetime = madrid_tz.localize(naive_datetime)
    utc_datetime = localized_datetime.astimezone(utc_tz)
    return utc_datetime.strftime("%Y-%m-%d %H:%M:%S")


# caching data for some time to reduce the number of Tinybird API hits
@st.cache_data(ttl=config.DATA_CACHE_SECONDS)
def load_data(
    pipe_name: str,  # the name of the Tinybird PIPE
    filter_max_date: str | None,
    filter_sensor: int | None = None,
    local_time: bool = False,
) -> pd.DataFrame | None:
    """Load data from the given Tinybird pipe name.

    Some optional filters can be provided.
    A None value can be returned if there are no rows.
    """
    params: dict = {}
    if filter_max_date:
        if not local_time:
            filter_max_date = _date_to_utc(filter_max_date)
        params["date"] = filter_max_date
    if filter_sensor:
        params["sensor"] = filter_sensor
    logger.info(f"Retrieving {pipe_name} data from Tinybird: {params}")
    params["token"] = config.TINYBIRD_TOKEN
    url = f"{config.TINYBIRD_API}{pipe_name}.csv?{urllib.parse.urlencode(params)}"
    logger.info(f"retrieving url {url}")
    return _process(pd.read_csv(url))
