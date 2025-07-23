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

def build_rain_graphic_circular(next_rain_date_str, rain_prob):
    if not next_rain_date_str:
        return {
            "family": "graphicCircular",
            "class": "CLKComplicationTemplateGraphicCircularStackText",
            "line1": "🌞",
            "line2": "Dry"
        }

    try:
        day_str = datetime.strptime(next_rain_date_str, "%Y-%m-%d").strftime("%a")  # e.g. "Tue"
    except Exception:
        day_str = "N/A"

    return {
        "family": "graphicCircular",
        "class": "CLKComplicationTemplateGraphicCircularStackText",
        "line1": "🌧️",
        "line2": f"{day_str} {rain_prob}%"
    }

def build_complication_json(watch_name, severity, mesoscale_prob, max_rain_prob, next_rain_date=None, next_rain_prob=0):
    short_name = get_short_watch_name(watch_name)
    emoji = get_emoji_by_severity(severity)

    rain_complication = build_rain_graphic_circular(next_rain_date, next_rain_prob)

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

    for alert_date_str, alert in rainalerts.items():
        prob = alert.get("probability", 0)
        if prob and prob > max_rain_prob:
            max_rain_prob = prob
        try:
            alert_date = datetime.strptime(alert_date_str, "%Y-%m-%d")
            if (not next_rain_date or alert_date < next_rain_date) and prob > 0:
                next_rain_date = alert_date
                next_rain_prob = prob
        except Exception:
            continue

    next_rain_date_str = next_rain_date.strftime("%Y-%m-%d") if next_rain_date else None

    return {
        "watch_name": watch_name,
        "severity": severity,
        "mesoscale_probability": mesoscale_prob,
        "max_rain_probability": max_rain_prob,
        "next_rain_date": next_rain_date_str,
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
