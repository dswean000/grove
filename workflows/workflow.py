#!/usr/bin/env python3

import os
import json
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import sys

from main import get_watches, get_mesoscales, get_max_risk, get_forecast

load_dotenv("locations.env")

# Constants and mappings
# Rank the CAP "severity" values
SEVERITY_RANK = {
    "Extreme": 4,
    "Severe": 3,
    "Moderate": 2,
    "Minor": 1,
    "Unknown": 0
}

# Map severity levels into a 2x2 classification
# You can swap these out for whatever emojis you want
SEVERITY_EMOJI = {
    "Extreme": "🟥",   # red square
    "Severe": "🟧",    # orange square
    "Moderate": "🟨",  # yellow square
    "Minor": "🟩",     # green square
    "Unknown": "⚪"    # fallback
}

def classify_watch(watches):
    """
    Return the most severe watch and its corresponding emoji.
    """
    most_severe_event = None
    most_severe_severity = "Unknown"
    highest_rank = -1
    
    for event, details in watches.items():
        severity = details.get("severity", "Unknown")
        rank = SEVERITY_RANK.get(severity, 0)
        if rank > highest_rank:
            highest_rank = rank
            most_severe_event = event
            most_severe_severity = severity
    
    emoji = SEVERITY_EMOJI.get(most_severe_severity, "⚪")
    return most_severe_event, emoji

def rain_emoji_for_alert(alert_date_str):
    alert_date = datetime.strptime(alert_date_str, "%Y-%m-%d").date()
    central_now = datetime.now(ZoneInfo("America/Chicago")).date()

    if alert_date == central_now:
        return "🔵"  # Blue circle for today
    elif alert_date == central_now + timedelta(days=1):
        return "🟦"  # Dark gray circle for tomorrow
    elif alert_date == central_now + timedelta(days=2):
        return "🔹"  # Dark gray circle for tomorrow
    else:
        return "⚪"  # White circle for later

def spc_risk_emoji(risk_level):
    mapping = {
        0: "⚪",  # No risk
        1: "⚪",  # General storms
        2: "🟩",  # Non-severe t-storms
        3: "🟢",  # Marginal
        4: "🟡",  # Slight
        5: "🟠",  # Enhanced
        6: "🔴",  # Moderate
        7: "🟥",  # High
    }

    # ✅ Handle dicts: pull nested "risk_level"
    if isinstance(risk_level, dict):
        risk_level = risk_level.get("risk_level", 0)

    try:
        rl = int(risk_level)
    except Exception:
        rl = 0

    return mapping.get(rl, "⚪")


from datetime import datetime
from zoneinfo import ZoneInfo

from datetime import datetime
from zoneinfo import ZoneInfo

def build_2x2_emoji_grid(spc_risk, rain_emoji, watches, mesoscale_active, has_midnighthigh):
    spc_emoji = spc_risk_emoji(spc_risk)

    # ✅ classify_watch works off the watches dict you already simplified
    top_watch, watch_emoji = classify_watch(watches)

    if mesoscale_active:
        mesoscale_emoji = "🛑"
    elif has_midnighthigh:
        mesoscale_emoji = "⚫"
    else:
        mesoscale_emoji = "⚪"

    # ✅ If all four are "no risk" / white, show sysdate in Central Time
    if spc_emoji == "⚪" and rain_emoji == "⚪" and watch_emoji == "⚪" and mesoscale_emoji == "⚪":
        now_ct = datetime.now(ZoneInfo("America/Chicago"))
        time_str = now_ct.strftime("%H:%M")  # 24-hour format
        return {
            "family": "graphicCircular",
            "class": "CLKComplicationTemplateGraphicCircularStackText",
            "line1": time_str
        }

    return {
        "family": "graphicCircular",
        "class": "CLKComplicationTemplateGraphicCircularStackText",
        "line1": f"{spc_emoji} {rain_emoji}",
        "line2": f"{watch_emoji} {mesoscale_emoji}"
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

def get_emoji_by_severity(severity):
    return SEVERITY_EMOJI.get(severity, "No")

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

    midnighthigh = forecast_data.get("midnighthigh", {})
    has_midnighthigh = bool(midnighthigh)



    max_rain_prob = 0
    max_rain_time = "N/A"
    rain_emoji = "⚪"
    if rainalerts:
        first_date_str = next(iter(rainalerts.keys()))
        first_alert = rainalerts[first_date_str]
        max_rain_prob = first_alert.get("probability", 0)
        max_rain_time = first_alert.get("start_time", "N/A")
        rain_emoji = rain_emoji_for_alert(first_date_str)

    rain_in_3days = max_rain_prob > 30

    has_watch = bool(watch_name)

    try:
        mesoscale_active = int(mesoscale_prob) > 0
    except Exception:
        mesoscale_active = False

    spc_day1_risk = risk.get("day1", {"description": "None", "risk_level": 0})
    spc_day2_risk = risk.get("day2", {"description": "None", "risk_level": 0})

    return {
        "watch_name": watch_name,
        "severity": severity,
        "mesoscale_active": mesoscale_active,
        "mesoscale_probability": mesoscale_prob,
        "max_rain_probability": max_rain_prob,
        "max_rain_time": max_rain_time,
        "rain_in_3days": rain_in_3days,
        "rain_emoji": rain_emoji,
        "has_watch": has_watch,
        "spc_day1_risk": spc_day1_risk,
        "spc_day2_risk": spc_day2_risk,
        "watches": watches,
        "has_midnighthigh": has_midnighthigh,      # ✅ already added
        "midnighthigh": midnighthigh               # ✅ NEW
    }



def build_complication_json(data):
    watches = data.get("watches", {})
    has_watch = bool(watches)

    emoji = get_emoji_by_severity(data.get("severity", "Unknown"))
    emoji_grid = build_2x2_emoji_grid(
        simplified["spc_day1_risk"],
        simplified["rain_emoji"],
        simplified["watches"],
        simplified["mesoscale_active"],
        simplified["has_midnighthigh"]
    )



    midnighthigh_text = ""
    if data.get("midnighthigh"):   # if it’s not empty
        # Format the dict into readable text
        mh_items = []
        for k, v in data["midnighthigh"].items():
            mh_items.append(f"{k}: {v}")
        midnighthigh_text = "\nMidnight High: " + ", ".join(mh_items)


    if watches and isinstance(watches, dict):
        active_watches = ", ".join(
            watch.get("headline", key) if isinstance(watch, dict) else key
            for key, watch in watches.items()
        )
    else:
        active_watches = "None"

    # Format timestamp helper
    def format_timestamp(dt):
        if sys.platform.startswith('win'):
            return dt.strftime("%a %m/%d %#I:%M%p CT")
        else:
            return dt.strftime("%a %m/%d %-I:%M%p CT")

    central_time = datetime.now(ZoneInfo("America/Chicago"))
    formatted_time = format_timestamp(central_time)

    meso_active = data.get('mesoscale_active')
    meso_active_str = "Yes" if meso_active else "No"
    meso_prob_line = f"Mesoscale Probability: {data.get('mesoscale_probability', 0)}%" if meso_active else ""

    body_text = (
        f"{formatted_time}\n"
        f"Watches: {active_watches}\n"
        f"Mesoscale Active: {meso_active_str}\n"
        f"{meso_prob_line}\n"
        f"Rain Chance: {data.get('max_rain_time', 'N/A')} ({data.get('max_rain_probability', 0)}%)\n"
        f"SPC Day 1 Risk: {data.get('spc_day1_risk', {}).get('description', 'None')} (Level {data.get('spc_day1_risk', {}).get('risk_level', 0)})\n"
        f"SPC Day 2 Risk: {data.get('spc_day2_risk', {}).get('description', 'None')} (Level {data.get('spc_day2_risk', {}).get('risk_level', 0)})\n"
        f"Midnight High: {midnighthigh_text}"  
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
            emoji_grid
        ]
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

    output_path = os.path.join(os.path.dirname(__file__), 'output.json')
    print(f"Writing to: {os.path.abspath(output_path)}")

    with open(output_path, "w") as f:
        json.dump(complication_json, f, indent=2)
        print("✅ output.json updated at", datetime.now())

if __name__ == "__main__":
    main()
