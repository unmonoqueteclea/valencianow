import base64
import datetime
import json
import os
import urllib.parse
from functools import lru_cache

import pandas as pd
import pytz
import requests

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


def decode_baliza_payload(encoded: str) -> dict:
    """Decode XOR-encoded baliza API response."""
    decoded_bytes = base64.b64decode(encoded)
    key = "utf-8"
    result = bytearray()
    for i, byte in enumerate(decoded_bytes):
        result.append(byte ^ ord(key[i % len(key)]))
    return json.loads(result.decode("utf-8"))


def load_balizas_data() -> pd.DataFrame | None:
    """Fetch baliza V16 (emergency traffic beacon) data from external API.

    Filters for active balizas in Valencia province only.
    """
    url = "https://api.mapabalizasv16.es/api/v16"
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,es;q=0.8",
        "cache-control": "no-cache",
        "origin": "https://mapabalizasv16.es",
        "pragma": "no-cache",
        "referer": "https://mapabalizasv16.es/",
        "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Brave";v="144"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "sec-gpc": "1",
        "x-api-key": "1j74ls84yj",
    }

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    data = decode_baliza_payload(response.text)
    df = pd.DataFrame(data["balizas"])
    # Normalize to standard columns
    df[COL_LAT] = pd.to_numeric(df["lat"])
    df[COL_LON] = pd.to_numeric(df["lon"])
    df["firstSeen"] = pd.to_datetime(df["firstSeen"])
    df["lastSeen"] = pd.to_datetime(df["lastSeen"])
    logger.info(f"Loaded {len(df)} balizas")
    # Filter for Valencia province (both "Valencia" and "València" spellings)
    df = df[df["provincia"].str.lower().str.contains("valencia", na=False)]
    logger.info(f"Filtered to {len(df)} balizas in Valencia province")
    # Filter for active status - check various possible active status values
    active_statuses = ["activa", "active", "activado", "on", "true", "1", "yes"]
    df = df[df["status"].str.lower().isin(active_statuses)]
    logger.info(f"Filtered to {len(df)} active balizas in Valencia province")
    # Add icon_data column for pydeck IconLayer
    # Using a real baliza V16 image as data URI to avoid CORS issues
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    img_path = os.path.join(static_dir, "baliza_v16.png")
    with open(img_path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode("utf-8")
    img_url = f"data:image/png;base64,{img_data}"
    icon_mapping = {
        "url": img_url,
        "width": 256,
        "height": 256,
        "anchorY": 128,
        "anchorX": 128,
    }
    df["icon_data"] = [icon_mapping] * len(df)
    return df  # type: ignore


@lru_cache(maxsize=1)
def load_sensor_addresses() -> dict:
    """Load sensor addresses from JSON file.

    Cached to avoid reading file multiple times.
    Returns empty dict if file doesn't exist (graceful degradation).
    """
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    json_path = os.path.join(static_dir, "sensor_addresses.json")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Sensor addresses file not found at {json_path}")
        return {"sensors": {}}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing sensor addresses JSON: {e}")
        return {"sensors": {}}


def get_sensor_display_name(sensor_id: int | str, sensor_type: str) -> str:
    """Get display name for a sensor (ID - Address format).

    Falls back to just sensor ID if address not found.
    """
    addresses = load_sensor_addresses()
    key = f"{sensor_type}_{sensor_id}"

    sensor_data = addresses.get("sensors", {}).get(key)
    if sensor_data:
        return sensor_data.get("display_name", str(sensor_id))

    return str(sensor_id)
