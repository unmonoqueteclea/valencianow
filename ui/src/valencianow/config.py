import os
import pathlib
import typing
import urllib.parse

import pandas as pd

APP_NAME = "valencia now"
USE_CACHED_DATA = False
TINYBIRD_API = "https://api.tinybird.co/v0/pipes/"
TINYBIRD_TOKEN = os.environ["TINYBIRD_TOKEN_VLC"]
TINYBIRD_LOGO = "https://github.com/unmonoqueteclea/valencianow/blob/main/ui/res/tinybird-logo.png?raw=true"
STREAMLIT_LOGO = "https://github.com/unmonoqueteclea/valencianow/blob/main/ui/res/streamlit-logo.png?raw=true"

SOURCE_CARS_NOW = "https://valencia.opendatasoft.com/explore/dataset/punts-mesura-trafic-espires-electromagnetiques-puntos-medida-trafico-espiras-ele/"
SOURCE_BIKES_NOW = "https://valencia.opendatasoft.com/explore/dataset/punts-mesura-bicis-espires-electromagnetiques-puntos-medida-bicis-espiras-electr/"

CACHE_PIPES = set(["cars_now", "bikes_noe"])


def _with_lat_lon(df: pd.DataFrame) -> typing.Optional[pd.DataFrame]:
    if df.shape[0] > 0:
        if "point" in df.columns:
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
    max_datetime: typing.Optional[str],
    sensor: typing.Optional[int] = None,
    use_cached_data: bool = USE_CACHED_DATA,
) -> typing.Optional[pd.DataFrame]:
    """Load data from the given Tinybird pipe name.

    If use_cached_data, return if possible existing cached data (not
    applying where we filter by a max datetime or sensor).

    """
    cached = pathlib.Path(f"{pipe_name}.csv")
    if not max_datetime and use_cached_data and cached.exists():
        return pd.read_csv(cached)
    params: dict = {"token": TINYBIRD_TOKEN}
    if max_datetime:
        params["date"] = max_datetime
    if sensor:
        params["sensor"] = sensor
    url = f"{TINYBIRD_API}{pipe_name}.csv?{urllib.parse.urlencode(params)}"
    print(f"retrieving {pipe_name} data from Tinybird: {url}")
    df = _with_lat_lon(pd.read_csv(url))
    if pipe_name in CACHE_PIPES and df is not None and not max_datetime:
        df.to_csv(cached)
    return df
