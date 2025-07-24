#!/usr/bin/env python3

import os
import json
from datetime import datetime, timezone
from main import get_watches, get_mesoscales, get_max_risk, get_forecast
from dotenv import load_dotenv

load_dotenv("locations.env")

lat = float(os.getenv("LATITUDE"))
lon = float(os.getenv("LONGITUDE"))

import sys

def format_hour(dt):
    if sys.platform.startswith('win'):
        return dt.strftime("%a %#I%p")  # Windows
    else:
        return dt.strftime("%a %-I%p")  # macOS/Linux


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

def spc_risk_emoji(risk_level):
    # risk_level expected as int or string number 0-4
    mapping = {
        0: "🟢",  # no/light risk (green)
        1: "🟢",
        2: "🟡",
        3: "🟠",
        4: "🔴"
    }
    try:
        rl = int(risk_level)
    except Exception:
        rl = 0
    return mapping.get(rl, "⚪")  # fallback white circle

def build_2x2_emoji_grid(spc_risk, rain_in_3days, has_watch, mesoscale_active):
    # Compose the 2x2 emoji grid lines (with padding spaces)
    line1 = f"{spc_risk_emoji(spc_risk)} {'🌧️' if rain_in_3days else '  '}"
    line2 = f"{'⚠️' if has_watch else '  '} {'🛑' if mesoscale_active else '  '}"
    
    return {
        "family": "modularSmall",
        "class": "CLKComplicationTemplateModularSmallStackText",
        "line1": line1,
        "line2": line2
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





def build_2x2_emoji_grid(spc_day1_risk, rain_in_3days, has_watch, mesoscale_active):
    spc_emoji_map = {
        0: "⚪",
        1: "🟩",
        2: "🛑",
        3: "🛑",
        4: "🛑",
    }

    def get_risk_level(risk):
        if isinstance(risk, dict):
            return risk.get("risk_level", 0)
        elif isinstance(risk, int):
            return risk
        else:
            return 0

    spc_emoji = spc_emoji_map.get(get_risk_level(spc_day1_risk), "⚪")
    rain_emoji = "🌧️" if rain_in_3days else "⚪"
    watch_emoji = "⚠️" if has_watch else "⚪"
    mesoscale_emoji = "🛑" if mesoscale_active else "⚪"

    return {
        "family": "graphicCircular",
        "class": "CLKComplicationTemplateGraphicCircularStackText",
        "line1": f"{spc_emoji} {rain_emoji}",
        "line2": f"{watch_emoji} {mesoscale_emoji}"
    }


def build_complication_json(data):
    watch_name = data.get("watch_name", "None")
    watches = data.get("watches", {})
    severity = data.get("severity", "Unknown")
    mesoscale_prob = data.get("mesoscale_probability", 0)
    max_rain_prob = data.get("max_rain_probability", 0)
    max_rain_time = data.get("max_rain_time", "N/A")  # e.g. "Friday 07/25 at 12AM"
    rain_in_3days = data.get("rain_in_3days", False)
    has_watch = data.get("has_watch", False)
    mesoscale_active = data.get("mesoscale_active", False)
    spc_day1_risk = data.get("spc_day1_risk", {"description": "None", "risk_level": 0})
    spc_day2_risk = data.get("spc_day2_risk", {"description": "None", "risk_level": 0})

    emoji = get_emoji_by_severity(severity)
    emoji_grid_complication = build_2x2_emoji_grid(spc_day1_risk, rain_in_3days, has_watch, mesoscale_active)

    # Format active watches list as comma separated string
    active_watches = ", ".join(watches.keys()) if watches else "None"

    # SPC risk info
    day1_desc = spc_day1_risk.get("description", "None")
    day1_level = spc_day1_risk.get("risk_level", 0)
    day2_desc = spc_day2_risk.get("description", "None")
    day2_level = spc_day2_risk.get("risk_level", 0)

    body_text = (
        f"{emoji} Watches: {active_watches}\n"
        f"Mesoscale Probability: {mesoscale_prob}%\n"
        f"Max Rain: {max_rain_time} ({max_rain_prob}%)\n"
        f"SPC Day 1 Risk: {day1_desc} (Level {day1_level})\n"
        f"SPC Day 2 Risk: {day2_desc} (Level {day2_level})\n"
        f"Active Watch: {'Yes' if has_watch else 'No'}\n"
        f"Mesoscale Active: {'Yes' if mesoscale_active else 'No'}"
    )

    return {
        "name": "Grove Weather",
        "showOnLockScreen": True,
        "views": [
            {
                "type": "text",
                "body": body_text
            }
        ],
        "families": [
            emoji_grid_complication
        ]
    }



def simplify_for_complication(data):
    watches = data.get("watches", {})
    mesoscales = data.get("mesoscales", {})
    forecast_data = data.get("forecast_data", {})
    risk = data.get("risk", {})

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
    for alert in rainalerts.values():
        prob = alert.get("probability", 0)
        if prob and prob > max_rain_prob:
            max_rain_prob = prob

    # For the grid, rain_in_3days is True if any rain prob > 20% (or your threshold)
    rain_in_3days = max_rain_prob > 20

    # has_watch = True if any watch/warning active
    has_watch = bool(watch_name)

    # mesoscale_active = True if mesoscale probability > 0
    try:
        mesoscale_active = int(mesoscale_prob) > 0
    except Exception:
        mesoscale_active = False

    # SPC day 1 risk, use the risk dict from get_weather_summary
    spc_day1_risk = risk.get("day1", 0)

    return {
        "watch_name": watch_name,
        "severity": severity,
        "mesoscale_probability": mesoscale_prob,
        "max_rain_probability": max_rain_prob,
        "rain_in_3days": rain_in_3days,
        "has_watch": has_watch,
        "mesoscale_active": mesoscale_active,
        "spc_day1_risk": spc_day1_risk
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

    complication_json = build_complication_json(simple)
    print("\nComplication JSON:")
    print(json.dumps(complication_json, indent=2))

    with open("output.json", "w") as f:
        json.dump(complication_json, f, indent=2)

if __name__ == "__main__":
    main()