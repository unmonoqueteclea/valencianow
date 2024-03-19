import os
import typing
import urllib.parse
from datetime import datetime

import pandas as pd
import streamlit as st

APP_NAME = "valencia-now"

TINYBIRD_API = "https://api.tinybird.co/v0/pipes/"
TINYBIRD_TOKEN = os.environ["TINYBIRD_TOKEN_VLC"]

TINYBIRD_LOGO = "https://github.com/unmonoqueteclea/valencianow/blob/main/ui/res/tinybird-logo.png?raw=true"
STREAMLIT_LOGO = "https://github.com/unmonoqueteclea/valencianow/blob/main/ui/res/streamlit-logo.png?raw=true"

# data sources
SOURCE_CARS_NOW = "https://valencia.opendatasoft.com/explore/dataset/punts-mesura-trafic-espires-electromagnetiques-puntos-medida-trafico-espiras-ele/"
SOURCE_BIKES_NOW = "https://valencia.opendatasoft.com/explore/dataset/punts-mesura-bicis-espires-electromagnetiques-puntos-medida-bicis-espiras-electr/"
SOURCE_AIR_NOW = "https://valencia.opendatasoft.com/explore/dataset/estacions-contaminacio-atmosferiques-estaciones-contaminacion-atmosfericas/"


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


# caching data for 20 minutes to reduce the number of Tinybird API hits
@st.cache_data(ttl=1200)
def load_data(
    pipe_name: str,
    filter_max_datetime: typing.Optional[str],
    filter_sensor: typing.Optional[int] = None,
) -> typing.Optional[pd.DataFrame]:
    """Load data from the given Tinybird pipe name.

    If use_cached_data, return if possible existing cached data
    (ignore if filter by a max datetime or sensor).

    """
    params: dict = {}
    if filter_max_datetime:
        params["date"] = filter_max_datetime
    if filter_sensor:
        params["sensor"] = filter_sensor
    print(f"{datetime.now()}: retrieving {pipe_name} data from Tinybird: {params}")
    params["token"] = TINYBIRD_TOKEN
    url = f"{TINYBIRD_API}{pipe_name}.csv?{urllib.parse.urlencode(params)}"
    return _preprocess(pd.read_csv(url))
