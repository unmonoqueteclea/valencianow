import os
import pathlib
import typing
import urllib.parse

import pandas as pd

APP_NAME = "valencia now"

# if true, the application will try to use cached data instead of
# hitting the API (for development purposes)
USE_CACHED_DATA = False
# the pipes that shoueld be cached
CACHE_PIPES = set(["cars_now", "bikes_now"])

TINYBIRD_API = "https://api.tinybird.co/v0/pipes/"
TINYBIRD_TOKEN = os.environ["TINYBIRD_TOKEN_VLC"]

TINYBIRD_LOGO = "https://github.com/unmonoqueteclea/valencianow/blob/main/ui/res/tinybird-logo.png?raw=true"
STREAMLIT_LOGO = "https://github.com/unmonoqueteclea/valencianow/blob/main/ui/res/streamlit-logo.png?raw=true"

# data sources
SOURCE_CARS_NOW = "https://valencia.opendatasoft.com/explore/dataset/punts-mesura-trafic-espires-electromagnetiques-puntos-medida-trafico-espiras-ele/"
SOURCE_BIKES_NOW = "https://valencia.opendatasoft.com/explore/dataset/punts-mesura-bicis-espires-electromagnetiques-puntos-medida-bicis-espiras-electr/"


def _preprocess(df: pd.DataFrame) -> typing.Optional[pd.DataFrame]:
    # if dataframe is empty, return None
    if df.shape[0] > 0:
        if "point" in df.columns:
            # convert point in to lat and lon
            df[["lat", "lon"]] = df["point"].str.split(",", expand=True)
            df["lat"] = pd.to_numeric(df["lat"])
            df["lon"] = pd.to_numeric(df["lon"])
            return df.drop(columns=["point"])
        if "day" in df.columns:
            df["day"] = pd.to_datetime(df["day"])
        if "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"])
        return df
    return None


def load_data(
    pipe_name: str,
    filter_max_datetime: typing.Optional[str],
    filter_sensor: typing.Optional[int] = None,
    use_cached_data: bool = USE_CACHED_DATA,
) -> typing.Optional[pd.DataFrame]:
    """Load data from the given Tinybird pipe name.

    If use_cached_data, return if possible existing cached data
    (ignore if filter by a max datetime or sensor).

    """
    cached = pathlib.Path(f"{pipe_name}.csv")
    if not filter_max_datetime and use_cached_data and cached.exists():
        return pd.read_csv(cached)
    params: dict = {"token": TINYBIRD_TOKEN}
    if filter_max_datetime:
        params["date"] = filter_max_datetime
    if filter_sensor:
        params["sensor"] = filter_sensor
    url = f"{TINYBIRD_API}{pipe_name}.csv?{urllib.parse.urlencode(params)}"
    print(f"retrieving {pipe_name} data from Tinybird: {url}")
    df = _preprocess(pd.read_csv(url))
    if pipe_name in CACHE_PIPES and df is not None and not filter_max_datetime:
        df.to_csv(cached)  # cache the data
    return df
