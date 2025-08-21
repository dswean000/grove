def get_watches(lat, long):
    alerts_url = f"https://api.weather.gov/alerts?active=true&point={lat},{long}"
    alerts_response = requests.get(alerts_url).json()
    
    #print(alerts_response)
    watches = {}  # Initialize watches as an empty dictionary

    for feature in alerts_response['features']:
        # Extract required properties
        props = feature['properties']
        event = props.get('event')
        if event:
            watches[event] = {
                "id"         : props.get('id'),
                "onset"      : props.get('onset'),
                "expires"    : props.get('expires'),
                "severity"   : props.get('severity'),
                "urgency"    : props.get('urgency'),
                "headline"   : props.get('headline'),
                "description": props.get('description')
            }

    return watches 


def get_mesoscales(latitude, longitude):
    import re
    import feedparser
    from shapely.geometry import Point, Polygon

    mesoscale_data = {
        "summary": None,
        "description": None,
        "probability": None
    }

    feed_url = "https://www.spc.noaa.gov/products/spcmdrss.xml"
    feed = feedparser.parse(feed_url)
    pattern = r"Probability of Watch Issuance\.\.\.(\d+)\spercent"

    for item in feed.entries:
        raw_desc = item.description

        # Extract CDATA block inside <pre> tags
        pre_match = re.search(r"<pre>(.*?)</pre>", raw_desc, re.DOTALL)
        if not pre_match:
            continue

        pre_text = pre_match.group(1)

        # Get coordinates block (series of 8-digit LATLON strings)
        coord_pattern = re.findall(r"\b\d{8}\b", pre_text)
        if not coord_pattern:
            continue

        formatted_coordinates = []
        for coord in coord_pattern:
            try:
                lat = float(coord[:2] + "." + coord[2:4])
                lon = -float(coord[4:6] + "." + coord[6:8])
                formatted_coordinates.append((lon, lat))  # Geo-style: (lon, lat)
            except Exception:
                continue

        if len(formatted_coordinates) < 3:
            continue

        polygon = Polygon(formatted_coordinates)
        point = Point(longitude, latitude)

        if polygon.contains(point):
            mesoscale_data["description"] = pre_text.strip()

            # Get SUMMARY section
            summary_match = re.search(r"SUMMARY\.\.\.(.*?)DISCUSSION", pre_text, re.DOTALL)
            if summary_match:
                mesoscale_data["summary"] = summary_match.group(1).strip()
            else:
                # fallback to start of message
                mesoscale_data["summary"] = pre_text[:200].strip()

            prob_match = re.search(pattern, pre_text)
            if prob_match:
                mesoscale_data["probability"] = prob_match.group(1)
            else:
                mesoscale_data["probability"] = "Unknown"

            break  # exit after first matching polygon

    if mesoscale_data["summary"] is None:
        mesoscale_data["summary"] = "None"
        mesoscale_data["probability"] = "0"

    return mesoscale_data




def get_max_risk(day, latitude, longitude):
    risk_data = {
        "description": None,
        "risk_level": None
    }


    outlook_urls = {
        1: "https://www.spc.noaa.gov/products/outlook/day1otlk_cat.nolyr.geojson",
        2: "https://www.spc.noaa.gov/products/outlook/day2otlk_cat.nolyr.geojson",
        3: "https://www.spc.noaa.gov/products/outlook/day3otlk_cat.nolyr.geojson",
    }

    # Check if the provided day is valid
    if day not in outlook_urls:
        raise ValueError("Invalid day. Supported values are 1, 2, or 3.")

    # Retrieve the outlook URL for the given day
    outlook_url = outlook_urls[day]

    # Fetch and parse the outlook response
    from workflow import safe_get_json  # or move safe_get_json into main.py directly
    outlook_response = safe_get_json(outlook_url, retries=1, delay=2)
    
    max_dn = float('-inf')
    risk_level_description = None
    
    risk_library = {
        2: ("Non-Severe T-Storms", 2),
        3: ("Marginal Risk", 3),
        4: ("Slight Risk", 4),
        5: ("Enhanced", 5),
        6: ("Moderate", 6),
        8: ("High", 8)}

    for feature in outlook_response["features"]:
        polygon = shape(feature["geometry"])
        
        # Check if the point is within the polygon
        if polygon.contains(Point(longitude, latitude)):
            dn = feature["properties"].get("DN")
            if dn is not None and dn > max_dn:
                max_dn = dn
                risk_level_description = risk_library.get(max_dn)

    if risk_level_description:
        risk_data["description"], risk_data["risk_level"] = risk_level_description

    return risk_data


# In[2]:


from collections import defaultdict
from datetime import datetime
import requests
import workflow

def get_forecast(latitude, longitude):
    forecast_data = {
        "midnighthigh": {},
        "rainalerts": {}
    }

    gridpoint_url = f"https://api.weather.gov/points/{latitude},{longitude}"
    gridpoint_response = requests.get(gridpoint_url).json()
    forecast_hourly_url = gridpoint_response["properties"]["forecastHourly"]
    forecast_hourly_response = requests.get(forecast_hourly_url).json()

    periods = forecast_hourly_response['properties']['periods']
    periods_by_date = defaultdict(list)
    for period in periods:
        date = period['startTime'].split('T')[0]
        periods_by_date[date].append(period)

    sorted_dates = sorted(periods_by_date.keys())[:-1]

    for date in sorted_dates:
        daily_periods = periods_by_date[date]
        max_temp_period = max(daily_periods, key=lambda p: p['temperature'])
        max_temp = max_temp_period['temperature']
        max_temp_hour = datetime.strptime(max_temp_period['startTime'], "%Y-%m-%dT%H:%M:%S%z").hour

        # Find the temperature at 5pm (17:00) if available
        temp_5pm = next((p['temperature'] for p in daily_periods if datetime.strptime(p['startTime'], "%Y-%m-%dT%H:%M:%S%z").hour == 17), None)

        # Check if the highest temperature is before noon
        if max_temp_hour < 12:
            forecast_data["midnighthigh"][date] = {
                "daily_high": max_temp,
                "hour_of_daily_high": max_temp_hour,
                "afternoon_high": temp_5pm
            }

    # Calculate rain alerts
    for period in periods:
        start_date = period['startTime'].split('T')[0]
        probability = period['probabilityOfPrecipitation']['value']

        if probability > 30:
            # Only add the first alert for each day
            if start_date not in forecast_data["rainalerts"]:
                start_time = datetime.strptime(period['startTime'], "%Y-%m-%dT%H:%M:%S%z")
                start_time_str = start_time.strftime("%A %m/%d at %I%p")

                forecast_data["rainalerts"][start_date] = {
                    'start_time': start_time_str, 
                    'probability': probability
                }



    return forecast_data

#from flask import jsonify
#from flask_caching import Cache  # If caching is needed
import requests   
import sys
import feedparser
import json
import re
from shapely.geometry import Point, shape, Polygon
from collections import defaultdict
from datetime import datetime

debug = 0

api_endpoint = "https://api.weather.gov"
zip_code = "66226"

if debug == 1:
    print("forecast_hourly_url",forecast_hourly_url)
    print(gridpoint_url)

# Retrieve the forecastZone value
if debug == 1:
    forecast_zone = gridpoint_response["properties"]["forecastZone"]
    forecast_office = gridpoint_response["properties"]["cwa"]

    print("Forecast Zone:", forecast_zone)
    print("Forecast Office:", forecast_office)


# Step 1- is there any severe risk for the next three days? 
#day1_risk = get_max_risk(cat1outlook_response)
#day2_risk = get_max_risk(cat2outlook_response)
#day3_risk = get_max_risk(cat3outlook_response)
#print("Day 1 Convective Risk: ",day1_risk)
#print("Day 2 Convective Risk: ",day2_risk)
#print("Day 3 Convective Risk: ",day3_risk)
#print("----------------------------------")
#https://www.spc.noaa.gov/misc/about.html#Convective%20Outlooks

#step 2- Mesoscales
summary = "" 
#current_mesoscales = get_mesoscales(latitude,longitude)
#print(current_mesoscales)

#if "None" not in summary:
#    summary = current_mesoscales[0]
#    probability = current_mesoscales[1]
#print("Current Mesoscale Discussion Summary:",summary)
#if len(probability) > 1:
 #   print("Watch Probability: ",probability,"Percent")

#step 3- Watches
#alerts = get_watches(alerts_response,latitude,longitude)
#print("Current Watches/Warnings: ",alerts)

#Step 4- Actual Forecasts...
midnighthigh = ""
#forecastData = get_forecast(forecast_hourly_response)
print(midnighthigh)

