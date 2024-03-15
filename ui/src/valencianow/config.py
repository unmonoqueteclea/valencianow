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


def _with_lat_lon(df: pd.DataFrame) -> pd.DataFrame:
    df[["lat", "lon"]] = df["point"].str.split(",", expand=True)
    df["lat"] = pd.to_numeric(df["lat"])
    df["lon"] = pd.to_numeric(df["lon"])
    return df.drop(columns=["point"])


def load_data(
    pipe_name: str, max_datetime: typing.Optional[str], use_cached_data: bool
) -> pd.DataFrame:
    """Load data from the given Tinybird pipe name.

    If use_cached_data, return if possible existing cached data (not
    applying where we filter by a max datetime).

    """
    cached = pathlib.Path(f"{pipe_name}.csv")
    if not max_datetime and use_cached_data and cached.exists():
        return pd.read_csv(cached)

    params = {"token": TINYBIRD_TOKEN}
    if max_datetime:
        params["date"] = max_datetime
    url = f"{TINYBIRD_API}{pipe_name}.csv?{urllib.parse.urlencode(params)}"
    print(f"retrieving {pipe_name} data from Tinybird: {url}")
    df = _with_lat_lon(pd.read_csv(url))
    if not max_datetime:
        df.to_csv(cached)
    return df
