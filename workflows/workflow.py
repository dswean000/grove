#!/usr/bin/env python3

import os
import json
from datetime import datetime, timezone
from main import get_watches, get_mesoscales, get_max_risk, get_forecast
from dotenv import load_dotenv

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

WATCH_NAME_MAP = {
    "Severe Thunderstorm Watch": "T-Storm",
    "Heat Advisory": "Heat",
    "Flood Watch": "Flood",
    "Tornado Watch": "Tor",
    "Winter Weather Advisory": "WWA",
    "Winter Storm Warning": "WSW"
}

SEVERITY_EMOJI = {
    "Extreme": "🔥",
    "Severe": "⚠️",
    "Moderate": "⚡",
    "Minor": "🟡",
    "Unknown": "❓",
    None: "❓"
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

def get_most_severe_watch(watches):
    most_severe_name = None
    highest_rank = -1

    for event, details in watches.items():
        severity = details.get("severity", "Unknown")
        rank = SEVERITY_RANK.get(severity, 0)
        if rank > highest_rank:
            highest_rank = rank
            most_severe_name = event

    return most_severe_name

def get_short_watch_name(full_name):
    return WATCH_NAME_MAP.get(full_name, full_name[:7])

def get_emoji_by_severity(severity):
    return SEVERITY_EMOJI.get(severity, "❓")

def parse_rainalert_start_time(start_time_str):
    # Example input: "Thursday 07/24 at 01PM"
    try:
        # Remove "Thursday " prefix to parse just "07/24 at 01PM"
        # Or parse whole string with a matching format string:
        dt = datetime.strptime(start_time_str, "%A %m/%d at %I%p")
        # Format as "Thu 1PM"
        return dt.strftime("%a %#I%p")  # Use %-I on Unix/macOS, %#I on Windows
    except Exception:
        return "N/A"




def build_rain_graphic_circular(next_rain_date, next_rain_prob, mesoscale_prob):
    # If active mesoscale discussion, override with ⚠️
    if int(mesoscale_prob) > 0:
        return {
            "family": "graphicCircular",
            "class": "CLKComplicationTemplateGraphicCircularStackText",
            "line1": "⚠️",
            "line2": "Mesoscale"
        }

    # Default label if no date
    line2 = "Dry"
    if next_rain_date:
        try:
            # Try parsing ISO with time first
            if "T" in next_rain_date:
                dt = datetime.strptime(next_rain_date, "%Y-%m-%dT%H:%M:%S")
            else:
                dt = datetime.strptime(next_rain_date, "%Y-%m-%d")

            # Windows needs %#I (not %-I like on Unix)
            line2 = dt.strftime("%a %#I%p")  # e.g. "Thu 4PM"
        except Exception as e:
            print(f"Failed to parse next_rain_date: {next_rain_date} ({e})")

    return {
        "family": "graphicCircular",
        "class": "CLKComplicationTemplateGraphicCircularStackText",
        "line1": "🌧️",
        "line2": line2
    }



def build_complication_json(watch_name, severity, mesoscale_prob, max_rain_prob, next_rain_date=None, next_rain_prob=0):
    short_name = get_short_watch_name(watch_name)
    emoji = get_emoji_by_severity(severity)

    rain_complication = build_rain_graphic_circular(next_rain_date, next_rain_prob, mesoscale_prob)


    return {
        "name": "Grove Weather",
        "showOnLockScreen": True,
        "views": [
            {
                "type": "text",
                "body": f"{emoji} Watch: {watch_name}\nMesoscale: {mesoscale_prob}%\nRain: {max_rain_prob}%"
            }
        ],
        "families": [
            {
                "family": "modularSmall",
                "class": "CLKComplicationTemplateModularSmallStackText",
                "line1": short_name,
                "line2": f"{mesoscale_prob}%"
            },
            {
                "family": "modularLarge",
                "class": "CLKComplicationTemplateModularLargeStandardBody",
                "header": "Grove Wx",
                "body1": watch_name,
                "body2": f"Mesoscale: {mesoscale_prob}%, Rain: {max_rain_prob}%"
            },
            {
                "family": "graphicCircular",
                "class": "CLKComplicationTemplateGraphicCircularStackText",
                "line1": emoji,
                "line2": short_name
            },
            rain_complication,
            {
                "family": "utilitarianSmall",
                "class": "CLKComplicationTemplateUtilitarianSmallFlat",
                "text": f"{short_name} {mesoscale_prob}%"
            }
        ]
    }

def simplify_for_complication(data):
    watches = data.get("watches", {})
    mesoscales = data.get("mesoscales", {})
    forecast_data = data.get("forecast_data", {})

    watch_name = data.get("most_severe_watch")
    severity = "Unknown"
    if not watch_name and watches:
        watch_name = next(iter(watches), "None")
        severity = watches.get(watch_name, {}).get("severity", "Unknown")
    elif watch_name:
        severity = watches.get(watch_name, {}).get("severity", "Unknown")

    mesoscale_prob = mesoscales.get("probability", "0")

    rainalerts = forecast_data.get("rainalerts", {})

    max_rain_prob = 0
    next_rain_date = None
    next_rain_prob = 0

    for date_str, alert in rainalerts.items():
        prob = alert.get("probability", 0)
        if prob and prob > max_rain_prob:
            max_rain_prob = prob
            next_rain_date = alert.get("start_time")  # e.g. "Thursday 07/24 at 01PM"
            next_rain_prob = prob

    return {
        "watch_name": watch_name,
        "severity": severity,
        "mesoscale_probability": mesoscale_prob,
        "max_rain_probability": max_rain_prob,
        "next_rain_date": next_rain_date,
        "next_rain_probability": next_rain_prob,
    }


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
    print("\nSimplified data:")
    print(json.dumps(simple, indent=2))

    complication_json = build_complication_json(
        simple["watch_name"],
        simple["severity"],
        simple["mesoscale_probability"],
        simple["max_rain_probability"],
        simple.get("next_rain_date"),
        simple.get("next_rain_probability"),
    )
    print("\nComplication JSON:")
    print(json.dumps(complication_json, indent=2))

    with open("output.json", "w") as f:
        json.dump(complication_json, f, indent=2)

if __name__ == "__main__":
    main()
