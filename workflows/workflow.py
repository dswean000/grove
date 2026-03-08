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
SEVERITY_RANK = {
    "Extreme": 4,
    "Severe": 3,
    "Moderate": 2,
    "Minor": 1,
    "Unknown": 0,
    None: 0
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
    "Extreme": "🔴",
    "Severe": "🟠",
    "Moderate": "🟡",
    "Minor": "🟢",
    "Unknown": "⚫",
    None: "⚫"
}

def format_midnighthigh(date, data):
    """
    Takes a date and a dict like:
    {'daily_high': 66, 'hour_of_daily_high': 0, 'afternoon_high': 65}
    Returns a clean string like:
    Midnight High for 2025-09-05: 66°F at 0:00 (Afternoon High: 65°F)
    """
    if not data:
        return f"Midnight High for {date}: No data"

    daily_high = data.get("daily_high", "N/A")
    hour = data.get("hour_of_daily_high", "N/A")
    afternoon_high = data.get("afternoon_high", "N/A")

    return (
        f"Midnight High for {date}: "
        f"{daily_high}°F at {hour}:00 "
        f"(Afternoon High: {afternoon_high}°F)"
    )



def rain_emoji_for_alert(alert_date_str):
    alert_date = datetime.strptime(alert_date_str, "%Y-%m-%d").date()
    central_now = datetime.now(ZoneInfo("America/Chicago")).date()

    if alert_date == central_now:
        return "🔵"  
    elif alert_date == central_now + timedelta(days=1):
        return "🟦"  
    elif alert_date == central_now + timedelta(days=2):
        return "🔹" 
    else:
        return "⚫"  

def spc_risk_emoji(risk_level):
    mapping = {
        0: "⚫",  # No risk
        1: "⚫",  # General storms
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

    return mapping.get(rl, "⚫")


from datetime import datetime
from zoneinfo import ZoneInfo

def build_2x2_emoji_grid(spc_risk, rain_emoji, severity, mesoscale_active, has_midnighthigh):
    spc_emoji = spc_risk_emoji(spc_risk)
    watch_emoji = SEVERITY_EMOJI.get(severity, "⚫")
    if mesoscale_active:
        mesoscale_emoji = "🛑"
    elif has_midnighthigh:
        mesoscale_emoji = "⚪"
    else:
        mesoscale_emoji = "⚫"

    # ✅ If all four are "no risk" / white, show sysdate in Central Time
    if spc_emoji == "⚫" and rain_emoji == "⚫" and watch_emoji == "⚫" and mesoscale_emoji == "⚫":
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
    rain_emoji = "⚫"
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

    # Build 4-day grid
    central_now = datetime.now(ZoneInfo("America/Chicago")).date()
    spc_by_day = [
        risk.get("day1", {"description": "None", "risk_level": 0}),
        risk.get("day2", {"description": "None", "risk_level": 0}),
        risk.get("day3", {"description": "None", "risk_level": 0}),
        None,  # day4: aspirational, not yet fetched
    ]
    four_days_grid = []
    for i in range(4):
        date = central_now + timedelta(days=i)
        date_str = date.isoformat()
        rain_e = "🔵" if date_str in rainalerts else "⚫"
        if i == 0:
            watch_e = SEVERITY_EMOJI.get(severity, "⚫")
            meso_e = "🛑" if mesoscale_active else ("⚪" if has_midnighthigh else "⚫")
        else:
            watch_e = "⚫"
            meso_e = "⚫"
        four_days_grid.append({
            "day_abbr": date.strftime("%a"),
            "spc_emoji": spc_risk_emoji(spc_by_day[i]) if spc_by_day[i] is not None else "⚫",
            "rain_emoji": rain_e,
            "watch_emoji": watch_e,
            "meso_emoji": meso_e,
        })

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
        "has_midnighthigh": has_midnighthigh,
        "midnighthigh": midnighthigh,
        "four_days_grid": four_days_grid,
    }



def build_modular_large_json(four_days_grid):
    header = "  ".join(d["day_abbr"] for d in four_days_grid)
    body1 = "  ".join(f"{d['spc_emoji']}{d['rain_emoji']}" for d in four_days_grid)
    body2 = "  ".join(f"{d['watch_emoji']}{d['meso_emoji']}" for d in four_days_grid)
    return {
        "name": "Grove 4-Day",
        "showOnLockScreen": True,
        "views": [],
        "families": [
            {
                "family": "modularLarge",
                "class": "CLKComplicationTemplateModularLargeStandardBody",
                "header": header,
                "body1": body1,
                "body2": body2,
            }
        ]
    }


def build_complication_json(data):
    watches = data.get("watches", {})
    watch_name = data.get("watch_name", None)
    severity = data.get("severity", "Unknown")

    emoji_grid = build_2x2_emoji_grid(
        data.get("spc_day1_risk"),
        data.get("rain_emoji", "⚫"),
        severity,                          # ✅ Pass actual severity here
        data.get("mesoscale_active", False),
        data.get("has_midnighthigh", False)
    )

    midnighthigh_text = ""
    if data.get("midnighthigh"):
        mh = data["midnighthigh"]
        # There's usually only one date key, but handle multiple just in case
        mh_lines = []
        for date, details in mh.items():
            mh_lines.append(format_midnighthigh(date, details))
        midnighthigh_text = "\n" + "\n".join(mh_lines)


    # Active watches text
    if watches and isinstance(watches, dict):
        active_watches = ", ".join(
            watch.get("headline", key) if isinstance(watch, dict) else key
            for key, watch in watches.items()
        )
    else:
        active_watches = "None"

    # Timestamp formatting
    def format_timestamp(dt):
        if sys.platform.startswith('win'):
            return dt.strftime("%a %m/%d %#I:%M%p CT")
        else:
            return dt.strftime("%a %m/%d %-I:%M%p CT")

    central_time = datetime.now(ZoneInfo("America/Chicago"))
    formatted_time = format_timestamp(central_time)

    meso_active = data.get('mesoscale_active', False)
    meso_active_str = "Yes" if meso_active else "No"
    meso_prob_line = f"Mesoscale Probability: {data.get('mesoscale_probability', 0)}%" if meso_active else ""

    body_text = (
        f"{formatted_time}\n"
        f"Watches: {active_watches}\n"
        f"Mesoscale Active: {meso_active_str}\n"
        f"{meso_prob_line}\n"
        f"Rain Chance: {data.get('max_rain_time', 'N/A')} ({data.get('max_rain_probability', 0)}%)\n"
        f"SPC Day 1 Risk: {data.get('spc_day1_risk', {}).get('description', 'None')} "
        f"(Level {data.get('spc_day1_risk', {}).get('risk_level', 0)})\n"
        f"SPC Day 2 Risk: {data.get('spc_day2_risk', {}).get('description', 'None')} "
        f"(Level {data.get('spc_day2_risk', {}).get('risk_level', 0)})\n"
        f"{midnighthigh_text}"
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

    modular_json = build_modular_large_json(simple["four_days_grid"])
    modular_path = os.path.join(os.path.dirname(__file__), 'output_modular.json')
    with open(modular_path, "w") as f:
        json.dump(modular_json, f, indent=2)
        print("✅ output_modular.json updated at", datetime.now())

if __name__ == "__main__":
    main()
