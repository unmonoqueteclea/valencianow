#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "geopy>=2.4.0",
#     "pandas>=2",
#     "requests",
# ]
# ///
"""Geocode sensor locations to addresses using geopy."""

import json
import os
import sys
import time
from io import StringIO

import pandas as pd
import requests
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim

# Constants
RATE_LIMIT_DELAY = 1.0  # seconds between requests
OUTPUT_PATH = "src/valencianow/static/sensor_addresses.json"

# Tinybird configuration
TINYBIRD_HOST = os.environ.get("TINYBIRD_HOST", "https://api.tinybird.co")
TINYBIRD_TOKEN = os.environ["TINYBIRD_TOKEN"]

# Pipe configurations (sensor_type: pipe_name, id_column)
PIPES = {
    "car": {"pipe": "cars_now", "id_col": "idpm"},
    "bike": {"pipe": "bikes_now", "id_col": "idpm"},
    "air": {"pipe": "air_now", "id_col": "_objectid"},
}


def fetch_sensor_data(pipe_name: str) -> pd.DataFrame:
    """Fetch sensor data from Tinybird pipe."""
    url = f"{TINYBIRD_HOST}/v0/pipes/{pipe_name}.csv"
    params = {"token": TINYBIRD_TOKEN}
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))


def extract_unique_sensors(df: pd.DataFrame, id_col: str, sensor_type: str):
    """Extract unique sensor IDs and coordinates."""
    sensors = []
    for sensor_id in df[id_col].dropna().unique():
        sensor_rows = df[df[id_col] == sensor_id]
        if "geo_point_2d" in sensor_rows.columns:
            geo_point = sensor_rows["geo_point_2d"].iloc[0]
            if pd.notna(geo_point):
                lat, lon = map(float, geo_point.split(","))
                sensors.append(
                    {
                        "sensor_id": str(int(sensor_id)),
                        "sensor_type": sensor_type,
                        "lat": lat,
                        "lon": lon,
                    }
                )
    return sensors


def format_address(raw_address: dict) -> str:
    """Format geocoded address for display (Spanish addresses)."""
    parts = []
    # Street address
    if "road" in raw_address:
        parts.append(raw_address["road"])
    elif "pedestrian" in raw_address:
        parts.append(raw_address["pedestrian"])
    # Neighborhood/suburb
    if "suburb" in raw_address:
        parts.append(raw_address["suburb"])
    elif "neighbourhood" in raw_address:
        parts.append(raw_address["neighbourhood"])
    # City
    if "city" in raw_address:
        parts.append(raw_address["city"])
    return ", ".join(parts[:3]) if parts else "Valencia"


def geocode_location(geolocator, lat, lon, sensor_id, sensor_type):
    """Reverse geocode a single location with retry logic."""
    max_retries = 3
    retry_delay = 2.0

    for attempt in range(max_retries):
        try:
            time.sleep(RATE_LIMIT_DELAY)  # Enforce 1 req/sec
            location = geolocator.reverse(f"{lat}, {lon}", language="es")

            if location and location.raw.get("address"):
                address = format_address(location.raw["address"])
                return {
                    "sensor_type": sensor_type,
                    "lat": lat,
                    "lon": lon,
                    "address": address,
                    "display_name": f"{sensor_id} - {address}",
                }
        except GeocoderTimedOut:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
        except GeocoderServiceError as e:
            print(f"⚠️  Service error for sensor {sensor_id}: {e}")
            break

    # Fallback if geocoding fails
    fallback_addr = f"Sensor {sensor_id}"
    return {
        "sensor_type": sensor_type,
        "lat": lat,
        "lon": lon,
        "address": fallback_addr,
        "display_name": sensor_id,
    }


def load_existing_addresses() -> dict:
    """Load existing sensor addresses if file exists."""
    if os.path.exists(OUTPUT_PATH):
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"📂 Loaded {len(data.get('sensors', {}))} existing addresses")
                return data.get("sensors", {})
        except (json.JSONDecodeError, FileNotFoundError):
            print("⚠️  Could not load existing addresses, starting fresh")
            return {}
    print("📂 No existing addresses file found, will geocode all sensors")
    return {}


def main():
    """Main execution flow."""
    print("🌍 Starting sensor geocoding process...")

    # Load existing addresses to avoid re-geocoding
    existing_results = load_existing_addresses()

    # Initialize geocoder
    geolocator = Nominatim(user_agent="valencianow_geocoder/1.0", timeout=10)

    # Collect all sensors
    all_sensors = []
    for sensor_type, config in PIPES.items():
        print(f"📡 Fetching {sensor_type} sensor data from {config['pipe']}...")
        df = fetch_sensor_data(config["pipe"])
        sensors = extract_unique_sensors(df, config["id_col"], sensor_type)
        print(f"   Found {len(sensors)} unique {sensor_type} sensors")
        all_sensors.extend(sensors)

    # Filter out sensors we already have
    sensors_to_geocode = []
    for sensor in all_sensors:
        key = f"{sensor['sensor_type']}_{sensor['sensor_id']}"
        if key not in existing_results:
            sensors_to_geocode.append(sensor)

    print(f"\n📊 Total sensors: {len(all_sensors)}")
    print(f"✅ Already geocoded: {len(all_sensors) - len(sensors_to_geocode)}")
    print(f"🆕 New sensors to geocode: {len(sensors_to_geocode)}")

    if not sensors_to_geocode:
        print("\n🎉 All sensors already geocoded! Nothing to do.")
        return

    print(f"⏱️  Estimated time: ~{len(sensors_to_geocode)} seconds (1 req/sec)")

    # Start with existing results
    results = existing_results.copy()
    for i, sensor in enumerate(sensors_to_geocode, 1):
        print(
            f"   [{i}/{len(sensors_to_geocode)}] Geocoding {sensor['sensor_type']} sensor {sensor['sensor_id']}..."
        )
        geocoded = geocode_location(
            geolocator,
            sensor["lat"],
            sensor["lon"],
            sensor["sensor_id"],
            sensor["sensor_type"],
        )
        key = f"{sensor['sensor_type']}_{sensor['sensor_id']}"
        results[key] = geocoded

    # Create output structure
    output = {
        "metadata": {
            "generated_at": pd.Timestamp.now().isoformat(),
            "total_sensors": len(results),
            "geocoding_service": "nominatim",
            "version": "1.0",
        },
        "sensors": results,
    }

    # Save to JSON file
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Geocoding complete! Saved to {OUTPUT_PATH}")
    print(f"📊 Total sensors geocoded: {len(results)}")


if __name__ == "__main__":
    if "TINYBIRD_TOKEN" not in os.environ:
        print("❌ Error: TINYBIRD_TOKEN environment variable not set")
        sys.exit(1)
    main()
