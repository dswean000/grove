#!/usr/bin/env python3
import json
from datetime import datetime
import pytz

# ----------------------------------------------------------------------
# Severity → Rank mapping (NWS "severity" values)
SEVERITY_RANK = {
    "Extreme": 4,
    "Severe": 3,
    "Moderate": 2,
    "Minor": 1,
    "Unknown": 0,
}

# ----------------------------------------------------------------------
# Helpers

def get_most_severe_watch(watches):
    """Return the name of the most severe watch/advisory from NWS data."""
    most_severe_name = None
    highest_rank = -1
    for event, details in watches.items():
        severity = details.get("severity", "Unknown")
        rank = SEVERITY_RANK.get(severity, 0)
        if rank > highest_rank:
            highest_rank = rank
            most_severe_name = event
    return most_severe_name


def build_2x2_emoji_grid(spc_day1_risk, rain_emoji, watches, mesoscale_active, has_midnighthigh):
    """
    Build a 2x2 grid of emojis based on weather data.
    You can customize the emojis as you see fit.
    """

    # Top-left: SPC day 1 risk
    risk_level = spc_day1_risk.get("risk_level")
    if risk_level is None:
        top_left = "⬜"
    elif risk_level == 0:
        top_left = "🟩"
    elif risk_level == 1:
        top_left = "🟨"
    elif risk_level == 2:
        top_left = "🟧"
    else:
        top_left = "🟥"

    # Top-right: rain signal
    top_right = rain_emoji or "⚪"

    # Bottom-left: most severe watch
    most_severe = get_most_severe_watch(watches) if watches else None
    if most_severe:
        severity = watches[most_severe]["severity"]
        if severity == "Extreme":
            bottom_left = "🟥"
        elif severity == "Severe":
            bottom_left = "🟧"
        elif severity == "Moderate":
            bottom_left = "🟨"
        elif severity == "Minor":
            bottom_left = "🟩"
        else:
            bottom_left = "⬜"
    else:
        bottom_left = "⬜"

    # Bottom-right: mesoscale discussion or midnight high
    if mesoscale_active:
        bottom_right = "🌀"
    elif has_midnighthigh:
        bottom_right = "🌙"
    else:
        bottom_right = "⬜"

    return f"{top_left}{top_right}\n{bottom_left}{bottom_right}"


def build_complication_json(simple):
    """Build Apple Watch complication JSON from simplified weather dict."""
    emoji_grid = build_2x2_emoji_grid(
        simple["spc_day1_risk"],
        simple["rain_emoji"],
        simple["watches"],
        simple["mesoscale_active"],
        simple["has_midnighthigh"],
    )

    # Time in 24h Central Time
    now_utc = datetime.now(pytz.utc)
    now_central = now_utc.astimezone(pytz.timezone("US/Central"))
    time_str = now_central.strftime("%H:%M")

    return {
        "complication": emoji_grid,
        "time": time_str,
    }


# ----------------------------------------------------------------------
# Entry Point

def main():
    # Simulated simplified input (normally comes from your pipeline)
    simple = {
        "watch_name": "Heat Advisory",
        "severity": "Moderate",
        "mesoscale_active": False,
        "mesoscale_probability": "0",
        "max_rain_probability": 31,
        "max_rain_time": "Tuesday 08/19 at 01PM",
        "rain_in_3days": True,
        "rain_emoji": "⚪",
        "has_watch": True,
        "spc_day1_risk": {"description": None, "risk_level": None},
        "spc_day2_risk": {"description": "Non-Severe T-Storms", "risk_level": 2},
        "watches": {
            "Heat Advisory": {
                "id": "urn:oid:xyz",
                "onset": "2025-08-16T13:00:00-05:00",
                "expires": "2025-08-16T19:00:00-05:00",
                "severity": "Moderate",
                "urgency": "Expected",
                "headline": "Heat Advisory issued ...",
                "description": "* WHAT...heat index values up to 106 expected.",
            }
        },
        "has_midnighthigh": False,
        "midnighthigh": {},
    }

    complication_json = build_complication_json(simple)
    print(json.dumps(complication_json, indent=2))


if __name__ == "__main__":
    main()
