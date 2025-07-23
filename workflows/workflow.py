#!/usr/bin/env python3

import os
import json
from datetime import datetime, timezone
from main import get_watches, get_mesoscales, get_max_risk, get_forecast

from dotenv import load_dotenv
import os

load_dotenv("locations.env")

lat = float(os.getenv("LATITUDE"))
lon = float(os.getenv("LONGITUDE"))

SEVERITY_RANK = {
    "Extreme": 4,
    "Severe": 3,
    "Moderate": 2,
    "Minor": 1,
    "Unknown": 0,
    None: 0  # In case severity is missing
}

def get_weather_summary(lat, lon):
    watches = get_watches(lat, lon)
    top_watch = get_most_severe_watch(watches)
    mesoscales = get_mesoscales(lat, lon)
    forecast_data = get_forecast(lat, lon)

    risk = {
        "day1": get_max_risk(1, lat, lon),
        "day2": get_max_risk(2, lat, lon),
        "day3": get_max_risk(3, lat, lon)
    }

    return {
        "metadata": {
            "latitude": lat,
            "longitude": lon,
            "updated": datetime.now(timezone.utc).isoformat()
        },
        "watches": watches,
        "most_severe_watch": top_watch,
        "mesoscales": mesoscales,
        "forecast_data": forecast_data,
        "risk": risk
    }


def simplify_for_complication(data):
    watches = data.get("watches", {})
    mesoscales = data.get("mesoscales", {})
    risk = data.get("risk", {})
    forecast_data = data.get("forecast_data", {})

    flags = {}

    flags["mesoscale_active"] = 0 if mesoscales.get("summary") in [None, "None"] else 1
    flags["mesoscale_probability"] = int(mesoscales.get("probability") or 0)

    for day_key in ["day1", "day2", "day3"]:
        level = risk.get(day_key, {}).get("risk_level")
        flags[f"risk_{day_key}"] = 0 if level in [None, 0] else 1

    rainalerts = forecast_data.get("rainalerts", {})
    flags["rain_alert"] = 1 if len(rainalerts) > 0 else 0

    max_rain_prob = 0
    max_rain_date = None
    for date, alert in rainalerts.items():
        prob = alert.get("probability", 0)
        if prob and prob > max_rain_prob:
            max_rain_prob = prob
            max_rain_date = date

    flags["max_rain_probability"] = max_rain_prob
    flags["max_rain_date"] = max_rain_date

    flags["updated"] = data.get("metadata", {}).get("updated", "")

    flags["most_severe_watch"] = data.get("most_severe_watch", "")


    return flags

def get_most_severe_watch(watches):
    """
    Return the name (key) of the watch with the highest severity.
    """
    most_severe_name = None
    highest_rank = -1

    for event, details in watches.items():
        severity = details.get("severity", "Unknown")
        rank = SEVERITY_RANK.get(severity, 0)

        if rank > highest_rank:
            highest_rank = rank
            most_severe_name = event

    return most_severe_name


def main():
    latitude = os.getenv("LATITUDE")
    longitude = os.getenv("LONGITUDE")
    if not latitude or not longitude:
        raise Exception("LATITUDE and LONGITUDE environment variables must be set.")

    latitude = float(latitude)
    longitude = float(longitude)

    summary = get_weather_summary(latitude, longitude)
    print("Full detailed JSON:")
    print(json.dumps(summary, indent=2))

    simple = simplify_for_complication(summary)
    print("\nSimplified JSON for complication:")
    print(json.dumps(simple, indent=2))


if __name__ == "__main__":
    main()
