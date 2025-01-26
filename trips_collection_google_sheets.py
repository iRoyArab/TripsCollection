import os
import re
import math
import ast
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import gpxpy
import gpxpy.gpx

import dash
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from dash import html, Input, Output
from dash import dcc
from dash import dash_table
from dash.dash_table import DataTable
import dash.exceptions as dash_exceptions

from pathlib import Path
from dash import dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate

# Google API imports
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------------
#  Google Sheets Setup
# ---------------------------------------------------------------------------------
global SPREADSHEET_ID
global RANGE_NAME

SERVICE_ACCOUNT_FILE = r"C:\Users\iroyp\OneDrive\שולחן העבודה\TELEGRAM\Telegram-Autoforwarder-master\trim-habitat-444716-p1-d86cbd7edca7.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=credentials)

SPREADSHEET_ID = '11NH7bL-o_fcGC1BbomkN4v-Cj8073GZ8MhJoQtq339c'
RANGE_NAME = 'Trip!A1:AB5000'

# ---------------------------------------------------------------------------------
#  Google Sheets I/O Helpers
# ---------------------------------------------------------------------------------
def load_data_from_gsheet():
    """
    Reads data from the Google Sheet and returns a DataFrame.
    Assumes first row is headers.
    """
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])
    if not values:
        return pd.DataFrame()
    else:
        df = pd.DataFrame(values[1:], columns=values[0])
        return df

def append_row_to_gsheet(row_data, headers):
    """
    Appends a single row (list) to the Google Sheet.
    row_data: list of values corresponding to the headers order.
    headers: list of column headers.
    """
    # Use append method to add a new row to the bottom
    request = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range='Trip!A1',
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body={'values': [row_data]}
    )
    request.execute()

def clear_gsheet_except_headers():
    """
    Clears all data except the header row. After clearing,
    only the header row will remain.
    """
    # Get the last row and column
    last_row = df_global.shape[0]  # Total number of rows
    last_col = df_global.shape[1]  # Total number of columns

    # Convert column index to Excel-style column letters
    from string import ascii_uppercase

    def column_number_to_letter(n):
        result = ""
        while n > 0:
            n, remainder = divmod(n - 1, 28)
            result = ascii_uppercase[remainder] + result
        return result

    last_col_letter = column_number_to_letter(last_col)
    dynamic_range = f"Trip!A1:{last_col_letter}{last_row}"
    # First get the current values
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=dynamic_range).execute()
    headers = result.get('values', [[]])[0] if result.get('values') else []

    # Clear entire sheet
    service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME
    ).execute()

    # Reinsert header row if headers exist
    if headers:
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range='Trip!A1',
            valueInputOption='RAW',
            body={'values': [headers]}
        ).execute()

def remove_trip_from_gsheet(trip_name):
    """
    Removes the row containing the given trip name from the sheet.
    Uses a batchUpdate request with DeleteDimensionRequest.
    Returns True if removed, False if not found.
    """
    try:
        # Load data
        df = load_data_from_gsheet()
        if df.empty or "Trip" not in df.columns or trip_name not in df["Trip"].values:
            return False

        # Find the index of the row to remove
        row_index = df.index[df["Trip"] == trip_name].tolist()[0]
        sheet_row_number = row_index + 2  # Offset for header and 0-based index

        # Prepare the delete request
        body = {
            "requests": [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": 0,  # Adjust this if not the first sheet
                            "dimension": "ROWS",
                            "startIndex": sheet_row_number - 1,
                            "endIndex": sheet_row_number
                        }
                    }
                }
            ]
        }

        # Execute the deletion
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=body
        ).execute()

        return True
    except Exception as e:
        print(f"Error removing trip: {e}")
        return False

def update_row(spreadsheet_id, row_number, values_ek, values_tab):
    # Define ranges for E:K and T:AB
    column_ranges = [
        f"Trip!E{row_number}:K{row_number}",
        f"Trip!T{row_number}:AB{row_number}"
    ]
    values_to_update = [values_ek, values_tab]

    # Debugging logs
    print(f"Updating row {row_number}")
    print(f"Values for E:K: {values_ek}")
    print(f"Values for T:AB: {values_tab}")

    # Update Google Sheets
    for range_name, values in zip(column_ranges, values_to_update):
        body = {'values': [values]}
        try:
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            print(f"Successfully updated range: {range_name}")
        except Exception as e:
            print(f"Error updating range {range_name}: {e}")





def safe_float_conversion(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def weighted_scores (scr_area,scr_access,scr_season,scr_challenge,scr_terrain,scr_view,
               scr_shade,scr_entry,scr_water,scr_nearby,scr_circular,scr_length,scr_incline,scr_decline,scr_incline_pre,
               scr_decline_pre,scr_walking,scr_how_far,scr_required_eq,scr_weather,scr_crowdness):
    score_val = {
        "Area": (scr_area * 0.1),
        "Accessibility": (scr_access * 0.05),
        "Season": (scr_season * 0.03),
        "Challenge": (scr_challenge * 0.08),
        "Terrain": (scr_terrain * 0.075),
        "View": (scr_view * 0.01),
        "Shade": (scr_shade * 0.075),
        "Entry Fee": (scr_entry * 0.025),
        "Water": (scr_water * 0.05),
        "Nearby Attractions": (scr_nearby * 0.05),
        "Circular?": (scr_circular * 0.05),
        "Trail Length": (scr_length * 0.075),
        "Incline": (scr_incline * 0.02),
        "Decline": (scr_decline * 0.015),
        "Incline Percentage": (scr_incline_pre * 0.015),
        "Decline Percentage": (scr_decline_pre * 0.01),
        "Walking Hours": (scr_walking * 0.025),
        "How Far?": (scr_how_far * 0.075),
        "Required EQ": (scr_required_eq * 0.075),
        "Weather": (scr_weather * 0.04),
        "Crowdness": (scr_crowdness * 0.05),
    }
    return sum (score_val.values())

global df_global
global df_copy
global df_copy2
# ---------------------------------------------------------------------------------
#  Global DataFrame loaded from GSheets
# ---------------------------------------------------------------------------------
df_global = load_data_from_gsheet()
df_copy = df_global.copy()

# ---------------------------------------------------------------------------------
#  Dash App Initialization
# ---------------------------------------------------------------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "The Trip Collection"

# ---------------------------------------------------------------------------------
#  Helpers / Utility Functions
# ---------------------------------------------------------------------------------
def compute_valid_score_count(df):
    
   
    if df.empty:
        return 0
    if "Trip" in df:
        counttr = pd.to_numeric(df["Trip"], errors='coerce')
        return counttr[counttr.notnull()].count()
    else:
        return 0

def exclude_empty_all_na(df):
    """
    Exclude columns that are entirely empty or contain only NA values.
    """
    if df.empty:
        return df
    return df.dropna(axis=1, how='all')

# --------------------------------------------------------------------
#   Trips Calculation & Validation
# --------------------------------------------------------------------
def trip_name_val(trip, df):
    if not trip:
        raise ValueError("Please insert a valid trip name.")
    # Only check for duplicates if DataFrame is not empty and 'Trip' column exists
    if not df.empty and "Trip" in df.columns:
        if trip in df["Trip"].values:
            raise ValueError("This trip is already in the data!")
    return trip

def mid_trail_coordinate(coord, link, season, df):
    if not coord:
        raise ValueError("Please insert a coordinate!")
    if "," not in coord:
        raise ValueError("Invalid coordinate string; a comma is missing.")
    # If DataFrame not empty, check for duplicates
    if not df.empty and "Coordinates" in df.columns:
        # Check if coordinate & link (and possibly season) is already used
        matching_coords = df[df["Coordinates"] == coord]
        if not matching_coords.empty:
            # If that exact link and season appear with the same coordinate
            if link in matching_coords["Trail Link"].values and season in matching_coords["Season"].values:
                raise ValueError("This coordinate is already in another trip with the same link/season!")
    return coord

def link_validity(link, df):
    if not link:
        raise ValueError("Please insert a valid link address.")
    if not link.startswith("https://israelhiking.osm.org.il/share/"):
        raise ValueError("Please insert a valid link to israelhiking.osm.org.il!")
    return link

def float_to_duration(value):
    hours = int(value)  
    minutes = round((value - hours) * 60)
    return f"{hours:02d}:{minutes:02d}"

def duration_to_int(duration):
    hours, minutes = map(int, duration.split(":"))
    return hours + minutes / 60

def naismith_rule(distance_km, ascent_m, descent_m, pace_kph):
    # Base walking time (time for distance only)
    base_time = distance_km / pace_kph
    avg_rest_time = base_time / 5
    # Elevation adjustment (1 hour for every 600 meters ascent)
    ascent_time = ascent_m / 600.0
    # Elevation adjustment for descent
    descent_time = descent_m / 1800.0
    total_time = base_time + ascent_time + descent_time + avg_rest_time
    hr = float_to_duration(total_time)
    return hr

def is_decimal_number(input_value):
    return isinstance(input_value, float) and not isinstance(input_value, (str, bool))

# --------------------------------------------------------------------
#   Dictionaries for Scoring
# --------------------------------------------------------------------
area_scores = {
    "Golan Heights - North-East Galilee": 10,
    "Golan Heights": 9.5,
    "Upper Galilee": 9.25,
    "Western Galilee": 9.2,
    "Galilee Center & The Kinerret": 9,
    "Lower Galilee": 8.75,
    "Carmel Mountains": 8.25,
    "Jerusalem Mountains": 8,
    "The Shfela Mountains": 7.5,
    "Eilat Mountains": 7,
    "The Dead Sea Mountains": 6.75,
    "South Negev Mountains": 6.5,
    "Arava Mountains": 6,
    "Northern Negav": 5,
    "Judea & Samaria Area": 4,
    "The Northen Coastal Plain": 3.5,
    "The Center Coastal Plain": 3,
    "The South Coastal Plain": 2.5
}

Accessibility = {
    "Open to All": 10,
    "Open, But with Army Coordination": 7.5,
    "Open Most of The Time, with Some Exceptions": 6,
    "Closed Most of The Time, with Some Exceptions": 4.5,
    "A Restricted Military Zone": 0,
}

Challenge = {
    "Very Challenging, with Lots of Obstacles in The Way": 10,
    "There's Some Challenge, but Most of it is in Average Challenge": 8,
    "There's some challenge, but Most of The Trail is Easy": 6.5,
    "Medium Challenge": 5,
    "Easy-Medium": 3.5,
    "Easy": 2,
    "No Challenge At All!": 0
}

Terrain = {
    "Mountainous region with lots of rivers and creeks": 10,
    "Mostly rivers, with some steep hills": 8,
    "Mostly high plattos, with some creeks": 6,
    "A coastly region, with some rivers": 5,
    "A plain area with some rivers and hills": 4,
    "A whole plain area": 2
}

View = {
    "Snowy mountains, lucious springs and rivers, lots of meadows and green": 13,
    "Vivid green mountains, lots of streams, and rocks": 10,
    "Bared Mountains with lots of flowing rivers": 8,
    "Green mountains, but no water nearby": 7.5,
    "Bared Mountains & Dry Rivers": 7,
    "Bared Mountains, but no rivers nearby": 6,
    "Deset mountains with some creeks": 5,
    "coastal area, shores and sea": 4,
    "Some small hills, creeks and open meadows": 3,
    "Urbanic View": 2
}

Shade = {
    "Mostly shaded, cooled and glimpses of sunshine occasionally": 10,
    "Fully shaded": 9,
    "Mostly shaded, but could be parts exposed to light": 8,
    "Half shaded, half exposed to sunlight": 6,
    "Most of it exposed to sunlight, occasionally shaded": 4,
    "Fully exposed to sunlight": 2
}

Entry_Fee = {
    "Free of charge": 10,
    "Free for most of the trail. with some unique locations for extra charge": 8,
    "Low-Medium charge, worths the money": 7,
    "Low-Medium charge, doesn't worth the money": 5.5,
    "High charge, but worth the money": 4,
    "High, mendatory and nothing special": 0
}

Water = {
    "Plenty of water, easy access, with an arranged entrance and many water activities in place": 13,
    "Lots of water, with several entrances, easy access": 10,
    "Some locations rich in waterfalls and pools, with many entry points throught the trail": 9,
    "Lots of locations with water along the trail, but hard to reach easily": 7.5,
    "Few points with water along the trail, not an easy access": 6,
    "Lots of points with dry, dirty pools along the way": 3,
    "Few points with even less water in them": 1.5,
    "None": 0
}

Nearby_attractions = {
    "Full of attractions nearby: wineries, viewpoints, food, pubs and resorts": 10,
    "Some attractions along the way, mostly wineries and restaurants": 8,
    "Few attractions nearby, mostly restaurants and hostels": 6,
    "One restaurant & hostel 50KM from the trail": 5,
    "One winery 50KM from the trail": 4,
    "Nothing special within 80KM from the trail": 2,
    "None": 0
}

circular = {
    "Yes": 10,
    "No": 0
}

def trail_length_score(trail_length):
    try:
        trail_length = float(trail_length)
    except (ValueError, TypeError):
        raise ValueError("Please insert a valid decimal number for the trail length.")
    if trail_length < 1 or trail_length > 30:
        raise ValueError("Not a relevant trail length, sorry :(")

    if 9 <= trail_length <= 12:
        return 10
    elif 7 <= trail_length < 9:
        return 9
    elif 12 < trail_length <= 15:
        return 8
    elif 5 <= trail_length < 7:
        return 7.5
    elif 3 <= trail_length < 5:
        return 6
    elif 15 < trail_length <= 20:
        return 5
    elif 20 < trail_length <= 25:
        return 4
    elif 25 < trail_length <= 30:
        return 3
    elif 2 <= trail_length < 3:
        return 2
    elif 1 <= trail_length < 2:
        return 1
    return 0

def incline_score(incline):
    try:
        incline = int(incline)
    except (ValueError, TypeError):
        raise ValueError("Please insert a valid number for the incline.")
    if incline < 1 or incline > 2500:
        raise ValueError("Not a relevant incline, sorry :(")

    if 550 <= incline <= 750:
        return 10
    elif 450 <= incline < 550:
        return 9
    elif 750 < incline <= 850:
        return 8
    elif 350 <= incline < 450:
        return 7.5
    elif 850 < incline <= 1000:
        return 6
    elif 250 <= incline < 350:
        return 5
    elif 150 <= incline < 250:
        return 4
    elif 1000 < incline <= 1200:
        return 3
    elif 1200 < incline <= 2500:
        return 2.5
    elif 1 <= incline < 150:
        return 2
    return 0

def decline_score(decline):
    try:
        decline = int(decline)
    except (ValueError, TypeError):
        raise ValueError("Please insert a valid number for the decline.")
    if decline < 1 or decline > 2500:
        raise ValueError("Not a relevant decline, sorry :(")

    if 550 <= decline <= 750:
        return 10
    elif 450 <= decline < 550:
        return 9
    elif 750 < decline <= 850:
        return 8
    elif 350 <= decline < 450:
        return 7.5
    elif 850 < decline <= 1000:
        return 6
    elif 250 <= decline < 350:
        return 5
    elif 150 <= decline < 250:
        return 4
    elif 1000 < decline <= 1200:
        return 3
    elif 1200 < decline <= 2500:
        return 2.5
    elif 1 <= decline < 150:
        return 2
    return 0

def inc_precentage_score(incline_pre):
    if not incline_pre:
        raise ValueError("Please enter an incline percentage of the trail.")
    try:
        incline_pre = float(incline_pre)
    except ValueError:
        raise ValueError("Incline percentage must be numeric.")
    if incline_pre < 0 or incline_pre > 100:
        raise ValueError("Incline percentage must be between 0 and 100.")

    if 40 < incline_pre <= 50:
        return 10
    elif 50 < incline_pre <= 60:
        return 9
    elif 60 < incline_pre <= 70:
        return 8
    elif 30 <= incline_pre <= 40:
        return 7
    elif 70 < incline_pre <= 80:
        return 6
    elif 80 < incline_pre <= 90:
        return 5
    elif 90 < incline_pre <= 100:
        return 4
    elif 20 <= incline_pre < 30:
        return 3
    elif 10 <= incline_pre < 20:
        return 2
    elif 0 <= incline_pre < 10:
        return 1
    return 0

def dec_precentage_score(decline_pre):
    if not decline_pre:
        raise ValueError("Please enter a decline percentage of the trail.")
    try:
        decline_pre = float(decline_pre)
    except ValueError:
        raise ValueError("Decline percentage must be numeric.")
    if decline_pre < 0 or decline_pre > 100:
        raise ValueError("Decline percentage must be between 0 and 100.")

    if 50 <= decline_pre < 60:
        return 10
    elif 40 <= decline_pre < 50:
        return 9
    elif 30 <= decline_pre < 40:
        return 8
    elif 60 <= decline_pre <= 70:
        return 7
    elif 20 <= decline_pre < 30:
        return 6
    elif 10 <= decline_pre < 20:
        return 5
    elif 0 <= decline_pre < 10:
        return 4
    elif 70 < decline_pre <= 80:
        return 3
    elif 80 < decline_pre < 90:
        return 2
    elif 90 <= decline_pre <= 100:
        return 1
    return 0

def kmh_validity(kmh):
    if kmh is None or kmh == '':
        raise ValueError("Please enter an average KMH.")
    try:
        kmh_float = float(kmh)
    except ValueError:
        raise ValueError("Please insert a valid decimal number for km/h.")
    if kmh_float <= 0 or kmh_float >= 15:
        raise ValueError("Invalid km/h! Must be > 0 and < 15.")
    return kmh_float

def walkinghr_scores(whr):
    if not whr:
        raise ValueError("Please provide a travel time in the format 'hh:mm'")
    try:
        hours, minutes = map(int, whr.split(":"))
    except ValueError:
        raise ValueError("Invalid format. Please provide time in 'hh:mm' format.")

    whr_value = hours + minutes / 60.0
    if 4.5 <= whr_value <= 5:
        return 10
    elif 4 < whr_value <= 4.5:
        return 9
    elif 3.5 <= whr_value <= 4:
        return 8
    elif 3 <= whr_value < 3.5:
        return 7
    elif 5 < whr_value <= 5.5:
        return 6.5
    elif 5.5 < whr_value <= 6.5:
        return 6
    elif 6.5 < whr_value <= 7.5:
        return 5.5
    elif 2.5 <= whr_value < 3:
        return 5
    elif 2 <= whr_value < 2.5:
        return 4.5
    elif 7.5 < whr_value <= 8.5:
        return 4
    elif 1.5 <= whr_value < 2:
        return 3
    elif 1 <= whr_value < 1.5:
        return 2.5
    elif 8.5 < whr_value <= 9:
        return 2
    elif 0 < whr_value < 1:
        return 1
    elif whr_value == 0 or whr_value > 9:
        return 0
    return 0

How_far_from_me = {
    "Half an hour drive": 10,
    "1 drive hour": 8.5,
    "1.5-2 drive hours": 7,
    "2.5 drive hours": 6,
    "2.5-3 drive hours": 4,
    "3.5 drive hours": 3,
    "3.5-4 drive hours": 2,
    "More than 4 drive hours": 0
}

Required_eq = {
    "Only a small bag with 1.5 liter bottle. hat, casual clothing": 10,
    "Could be a small bag, but packed with 3 liter of water, and food, casual clothing": 8.5,
    "Could be casual clothing, but must have a professional day-trip bagpack, with a hydration pack, small botlle, food and first-aid kit": 7,
    "Hiking clothing required, with a good pack and trekking poles": 6.5,
    "Hiking clothing, a fully load day-trip backpack, with 6 liter of water, kooking kit, food, first-aid kit": 5.5,
    "Fully equipped for a daytrip, including trekking poles": 4,
    "A professional hiking clothing, fully loaded 60 liter professional bagpack": 2.5,
}

Weather = {
    "Clear, an average of 18-20C": 10,
    "Clear, an average of 22-25C": 9,
    "Cloudly with some rain and snow, 8-10C": 8.5,
    "Cloudly, but dry with 17-20C": 8,
    "Cloudly with light rain, 16-18C": 7.5,
    "Clear, 27-30C": 6,
    "Cloudly with heavy rain, 23-25C": 5,
    "Cloudly with heavy rain, lower then 15C": 3,
    "Clear, 35-40C": 1.5,
    "Lower than 8C or Higher than 40C": 0
}

Season = {
    "Winter - Spring": 10,
    "Winter": 8.5,
    "Spring": 7,
    "Autumn - Winter": 5.5,
    "Autumn": 4,
    "Spring - Summer": 3,
    "Summer-Autumn": 2,
    "Summer": 1
}

Crowdness = {
    "Not crowded at all": 10,
    "Some hikers along the way, not really affecting the experience": 8.5,
    "Lots of hikers along the trail": 7,
    "Many families along the way, but there's still enough room for all": 6,
    "Not so many people along the way, but feels very crowded": 3,
    "Too many hikers, families and waste along the way, almost can't move": 0
}

# ---------------------------------------------------------------------------------
#   Styling
# ---------------------------------------------------------------------------------
background_style = {
    "background-image": "url('https://as2.ftcdn.net/v2/jpg/08/97/50/73/1000_F_897507396_zRg90Ih9yJzejFTWpolmh92eQvuZplme.jpg')",
    "background-size": "cover",
    "background-position": "center",
    "background-repeat": "no-repeat",
    "height": "150vh",
    "padding": "10px",
}
background_style4 = {
    "background-image": "url('https://as2.ftcdn.net/v2/jpg/08/97/50/73/1000_F_897507396_zRg90Ih9yJzejFTWpolmh92eQvuZplme.jpg')",
    "background-size": "cover",
    "background-position": "center",
    "background-repeat": "no-repeat",
    "height": "200vh",
    "padding": "10px",
}
container_style = {
    "background-color": "rgba(255, 255, 255, 0.8)",
    "border-radius": "50px",
    "padding": "15px",
    "box-shadow": "0px 8px 20px rgba(0, 0, 0, 0.3)",
    "width": "100%",
    "max-width": "2800px",
    "margin": "0 auto",
}

tab_style = {
    "background-color": "rgba(255, 255, 255, 0.5)",
    "background-image": "url('/assets/tab_nor.jpg')",
    "background-size": "cover",
    "background-position": "top",
    "background-repeat": "no-repeat",
    'color': 'white',
    'border-color': 'white',
    'font-size': '38px',
    "text-shadow": "1px 1px 2px black, -1px -1px 2px black, 1px -1px 2px black, -1px 1px 2px black"

}

selected_tab_style = {
    "background-color": "rgba(255, 255, 255, 0.5)",
    "background-image": "url('/assets/tab_sel.jpeg')",
    "background-size": "cover",
    "background-position": "top",
    'color': 'white',
    'font-size': '38px',
    'font-weight': 'bold',
    'border-color': 'red',
    "text-shadow": "1px 1px 2px black, -1px -1px 2px black, 1px -1px 2px black, -1px 1px 2px black"

}

heading_style = {
    "text-align": "center",
    "font-family": "Arial, sans-serif",
    "color": "#2C3E50",
    "margin-bottom": "20px",
}

card_style = {
   "background-image": "url('https://www.pixelstalk.net/wp-content/uploads/2016/08/Black-Backgrounds-HD-1920x1080-For-Desktop.jpg')" 
}

button_style = {
    "borderRadius": "50px",
    "width": "40%",
    "height": "80px",
    "margin": "750px auto auto -450px",
    "background-color": "#3498DB",
    "color": "black",
    "border": "2px solid black",
    "display": "block",
    "font-weight": "bold",
    "font-size": "32px"
}
button_style_tab5 = {
    "borderRadius": "50px",  # Makes the corners fully rounded
    "width": "40%",
    "height": "80px",
    "margin": "380px auto auto 50px",
    "background-color": "#3498DB",
    "color": "black",
    "border": "2px solid black",
    "display": "block",
    "font-weight": "bold",
    "font-size": "32px"
}

button_style_tab5_2 = {
    "borderRadius": "50px",  # Makes the corners fully rounded
    "width": "40%",
    "height": "80px",
    "margin": "-70px 0px auto 1000px",
    "background-color": "red",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "yellow",
    "textAlign": "center",
    "display": "block",
    "font-size": "20px"
}

button_style1 = {
    "borderRadius": "50px",
    "width": "26%",
    "height": "60px",
    "margin": "10px ",
    "background-color": "green",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center",
    "font-size": "32px"
}

button_style_2 = {
    "borderRadius": "50px",
    "width": "30%",
    "height": "60px",
    "margin": "-50px 0px auto 700px",
    "background-color": "red",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "yellow",
    "textAlign": "center",
    "display": "block",
    "font-size": "20px"
}

button_style3 = {
    "borderRadius": "50px",
    "width": "26%",
    "height": "60px",
    "margin": "50px 0 50px auto ",
    "background-color": "orange",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center",
    "font-size": "30px"
}

button_style3_tab5 = {
    "borderRadius": "50px",  # Makes the corners fully rounded
    "width": "46%",
    "height": "60px",
    "margin": "50px 0 50px auto ",
    "background-color": "orange",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center",
    "font-size": "30px"    
}

button_style4 = {
    "borderRadius": "50px",
    "width": "56%",
    "height": "60px",
    "margin": "-60px auto 500px 650px ",
    "background-color": "orange",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center",
    "font-size": "32px"
}

button_style6 = {
    "borderRadius": "50px",
    "width": "36%",
    "height": "60px",
    "margin": "25px 20px 70px  ",
    "background-color": "orange",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center",
    "font-size": "28px"
}

button_style7 = {
    "borderRadius": "50px",
    "width": "26%",
    "height": "60px",
    "margin": "25px 20px 70px  ",
    "background-color": "red",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center",
    "font-size": "28px"
}

button_style8 = {
    "borderRadius": "50px",
    "width": "26%",
    "height": "60px",
    "margin": "25px 20px 70px  ",
    "background-color": "orange",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center",
    "font-size": "28px"
}

button_style_11 ={
    "borderRadius": "50px",
    "width": "32%",
    "height": "60px",
    "margin": "10px ",
    "background-color": "green",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center",
    "font-size": "32px"  
}

button_style_11_tab5 ={
    "borderRadius": "50px",  # Makes the corners fully rounded
    "width": "62%",
    "height": "60px",
    "margin": "10px ",
    "background-color": "green",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center",
    "font-size": "32px"  
}

button_style9 = {
    "borderRadius": "50px",
    "width": "26%",
    "height": "60px",
    "margin": "25px 20px 70px  ",
    "background-color": "green",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center",
    "font-size": "28px"
}

button_style_filter = {
    "borderRadius": "50px",
    "width": "46%",
    "height": "60px",
    "margin": "25px -1200px 70px ",
    "background-color": "blue",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center",
    "font-size": "28px"
}

button_style0 = {
    "borderRadius": "50px",
    "width": "26%",
    "height": "60px",
    "margin": "10px ",
    "background-color": "red",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center",
    "font-size": "32px"
}

button_style13 = {
    "borderRadius": "50px",  # Makes the corners fully rounded
    "width": "46%",
    "height": "60px",
    "margin": "-190px auto auto 230px ",
    "background-color": "yellow",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "black",
    "textAlign": "center",
    "font-size": "30px"
}


font_style = {
    "font-weight": "bold",
}

output_style = {
    "margin-top": "30px",
    "font-family": "David, sans-serif",
    "color": "#2C3E50",
    "padding": "10px",
    "font-size": "25px",
}

# ---------------------------------------------------------------------------------
#   Layout
# ---------------------------------------------------------------------------------
def tab1_layout():

    # If CSV exists and has data, read it to get initial min/max for the RangeSliders
    df=df_global.copy()
    # Ensure "Trail Length" column is numeric
    df["Trail Length"] = pd.to_numeric(df["Trail Length"], errors="coerce")

    # Drop rows with invalid or missing "Trail Length" values
    df = df.dropna(subset=["Trail Length"])
    if not df.empty:
        # Create markers
        markers_israel = []
        for i, (coord, name) in enumerate(zip(df['Coordinates'], df['Trip'])):
            try:
                position = ast.literal_eval(coord)
                if isinstance(position, (list, tuple)) and len(position) == 2:
                    markers_israel.append(
                        dl.Marker(
                            position=position,
                            children=[dl.Popup(name)],
                            id="israel-mark-" + str(i)
                        )
                    )
            except (SyntaxError, ValueError):
                pass
    else:
        return "No DF Available"


    # If df is not empty, define some default range slider values
    if not df.empty:
        length_min = float(df["Trail Length"].min())
        length_max = float(df["Trail Length"].max())
        score_min = float(df["Total Score"].min())
        score_max = float(df["Total Score"].max())

    else:
        # fallback
        length_min, length_max = 0, 0
        score_min, score_max = 0, 0

    return html.Div(
        style=background_style,
        children=[

            dcc.Store(id='trip-data-store'),
            dbc.Container(
                style=container_style,
                children=[
                    html.H1("Trip Analysis", style=heading_style),
                    html.Hr(),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    # ---------- Trail Length Range ---------- #
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Trail Length Range (in KM)",
                                                           style={'font-weight': 'bold',
                                                                  'font-size': '24px',
                                                                  'color': 'white',
                                                                  'text-align': 'left'}
                                                           ),
                                            dbc.CardBody([
                                                dcc.RangeSlider(
                                                    id="length_slider",
                                                    min=length_min,
                                                    max=length_max,
                                                    step=0.01,
                                                    value=[length_min, length_max],  # initial range
                                                    tooltip={"placement": "bottom", "always_visible": True},
                                                )
                                            ]),
                                        ],
                                        style={
                                            "background-image": "url('https://www.pixelstalk.net/wp-content/uploads/2016/08/Black-Backgrounds-HD-1920x1080-For-Desktop.jpg')"
                                        }
                                    ),
                                    html.Br(),
                                    # ---------- Score Range ---------- #
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Score Range",
                                                           style={'font-weight': 'bold',
                                                                  'font-size': '24px',
                                                                  'color': 'white',
                                                                  'text-align': 'left'}
                                                           ),
                                            dbc.CardBody([
                                                dcc.RangeSlider(
                                                    id="score_slider",
                                                    min=score_min,
                                                    max=score_max,
                                                    step=0.0005,
                                                    value=[score_min, score_max],  # initial range
                                                    tooltip={"placement": "bottom", "always_visible": True},
                                                )
                                            ]),
                                        ],
                                        style={
                                            "background-image": "url('https://www.pixelstalk.net/wp-content/uploads/2016/08/Black-Backgrounds-HD-1920x1080-For-Desktop.jpg')"
                                        }
                                    ),
                                    html.Br(),
                                    dbc.Button("Update DB", id='update_db2',
                                                color='success',
                                                n_clicks=0,
                                                style=button_style1),  
                                    dbc.Button("Reset Filters", id='filt_res',
                                                color='success',
                                                n_clicks=0,
                                                style=button_style0),                                   
                                    html.Br(),
                                    html.H1("The Trips Map", style={'font-weight': 'bold'}),
                                    dl.Map(
                                        [
                                            dl.TileLayer(),
                                            dl.LayerGroup(
                                                id="Israel-map-layer",
                                                children=markers_israel
                                            )
                                        ],
                                        center=(32.2243079, 35.2682359),
                                        zoom=8,
                                        style={"width": "100%", "height": "550px", 'border': '2px solid black'}
                                    ),
                                    html.Br(),
                                    dbc.Col([
                                        html.Div([
                                            dbc.Label("The Trips List", style={'font-weight': 'bold', 'font-size': '24px'}),
                                            html.Br(),
                                            dcc.Dropdown(
                                                id='trips_list_2',
                                                options=[],
                                                value=None,
                                                className="form-control",
                                                style={"display": "inline-block", "width": "100%"}
                                            ),
                                            dbc.Button("Pick a Trip", id='trip_picker',
                                                       color='success',
                                                       n_clicks=0,
                                                       style=button_style4),
                                        ]),
                                    ], width=6),
                                ],
                                width=4  # Adjust column width as needed
                            ),
                            # ---------- Middle Stats Columns ---------- #
                            dbc.Col(
                                [
                                    html.H1("General Stats", style={'font-weight': 'bold'}),
                                    html.Br(),
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Highest Score Trip", style=font_style),
                                            dbc.CardBody(html.H4("", id='highest_score', className="card-title"))
                                        ],
                                        inverse=True,
                                        style=card_style
                                    ),
                                    html.Br(),
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Most Common View", style=font_style),
                                            dbc.CardBody(html.H4("", id='mcv', className="card-title",
                                                                 style={'font-size': '20px'}))
                                        ],
                                        style=card_style,
                                        inverse=True
                                    ),
                                    html.Br(),
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Most Common Travel Distance", style=font_style),
                                            dbc.CardBody(html.H4("", id='mcd', className="card-title"))
                                        ],
                                        style=card_style,
                                        inverse=True
                                    ),
                                    html.Br(),
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Most Common Travel Area", style=font_style),
                                            dbc.CardBody(html.H4("", id='mcta', className="card-title"))
                                        ],
                                        style=card_style,
                                        inverse=True
                                    ),
                                ],
                                width=2  # Adjust column width as needed
                            ),
                            dbc.Col(
                                [
                                    html.H1("", style={'font-weight': 'bold', 'margin-top': '55px'}),
                                    html.Br(),
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Trips Count", style=font_style),
                                            dbc.CardBody(html.H4("", id='check_trips', className="card-title"))
                                        ],
                                        inverse=True,
                                        style=card_style
                                    ),
                                    html.Br(),
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Average Trip Length", style=font_style),
                                            dbc.CardBody(html.H4("", id='average_length', className="card-title"))
                                        ],
                                        inverse=True,
                                        style=card_style
                                    ),
                                    html.Br(),
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Average Travel Time", style=font_style),
                                            dbc.CardBody(html.H4("", id='average_time', className="card-title"))
                                        ],
                                        style=card_style,
                                        inverse=True
                                    ),
                                    html.Br(),
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Most Challenging Trip", style=font_style),
                                            dbc.CardBody(html.H4("", id='mct', className="card-title"))
                                        ],
                                        style=card_style,
                                        inverse=True
                                    ),
                                ],
                                width=2  # Adjust column width as needed
                            ),
                            # ---------- IFrame & Details ---------- #
                            dbc.Col([
                                html.H1("Selected Trip Trail Map", style={'font-weight': 'bold'}),
                                html.Br(),
                                html.Iframe(
                                    id='picked_trail_map',
                                    src="https://israelhiking.osm.org.il/share/lXiAuFiwSa",
                                    style={
                                        "width": "100%",
                                        "height": "600px",
                                        "border": "2px solid black"
                                    }
                                ),
                                html.Br(),
                                html.Div(
                                    id='trip_details',
                                    style={
                                        'padding': '20px',
                                        'width': '810px',
                                        'height': '750px',
                                        'backgroundColor': '',
                                        'opacity': '100%',
                                        'border': '1px solid #444',
                                        'borderRadius': '5px',
                                    }
                                ),
                            ])
                        ]
                    )
                ]
            )
        ]
    )


# --------------- Callback --------------- #
@app.callback(
    [
        Output("Israel-map-layer", "children"),
        Output("highest_score", "children"),
        Output("mcv", "children"),
        Output("mcd", "children"),
        Output("mcta", "children"),
        Output("check_trips", "children"),
        Output("average_length", "children"),
        Output("average_time", "children"),
        Output("mct", "children"),

        # RangeSlider outputs for length
        Output("length_slider", "min"),
        Output("length_slider", "max"),
        Output("length_slider", "value"),
        Output("length_slider", "marks"),

        # RangeSlider outputs for score
        Output("score_slider", "min"),
        Output("score_slider", "max"),
        Output("score_slider", "value"),
        Output("score_slider", "marks"),

        Output("trips_list_2", "options"),
        Output("trips_list_2", "value"),
        Output("picked_trail_map", "src"),
        Output('trip_details', 'children'),
    ],
    [
        Input("length_slider", "value"),
        Input("score_slider", "value"),
        Input("trip_picker", "n_clicks"),
        Input("update_db2", "n_clicks"),
        Input("filt_res", "n_clicks"),
    ],
    State("trips_list_2", "value"),
    # Removed prevent_initial_call=True to allow callback on initial load
)
def update_tab1(length_value, score_value, n_clicks,update_clicks,reset_clicks, trips_list_value):
    ctx = dash.callback_context
    df = df_copy.copy()

    # Ensure "Trail Length" is numeric
    df["Trail Length"] = pd.to_numeric(df["Trail Length"], errors="coerce")
    # Drop rows with invalid or missing "Trail Length" values
    df = df.dropna(subset=["Trail Length"])

    # Ensure other necessary columns are numeric
    numeric_columns = ["Total Score", "Incline Degree", "Decline Degree"]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Drop rows with invalid or missing values in these columns if necessary
    df = df.dropna(subset=["Total Score", "Incline Degree", "Decline Degree"])

    # Prepare default (fallback) returns for an empty df
    markers_israel = []
    link_trail_src = dash.no_update
    trip_details_div = dash.no_update

    if not df.empty:
        min_length = float(df["Trail Length"].min())
        max_length = float(df["Trail Length"].max())
        min_score = float(df["Total Score"].min())
        max_score = float(df["Total Score"].max())
    else:
        min_length = 0
        max_length = 0
        min_score = 0
        max_score = 0

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
    if not ctx.triggered:

        # Build initial marks for sliders
        length_marks = {
            int(min_length): {'label': str(int(min_length)), 'style': {'font-size': '20px'}},
            int(max_length): {'label': str(int(max_length)), 'style': {'font-size': '20px'}}
        }
        score_marks = {
            int(min_score): {'label': str(int(min_score)), 'style': {'font-size': '20px'}},
            int(max_score): {'label': str(int(max_score)), 'style': {'font-size': '20px'}}
        }

        if df.empty:
            return (
                [],  # Israel-map-layer
                "",  # highest_score
                "",  # mcv
                "",  # mcd
                "",  # mcta
                "0 Trips",  # check_trips
                "0 KM",  # average_length
                "0 Hours",  # average_time
                "N/A",  # mct
                0,      # length_slider.min
                0,      # length_slider.max
                [0, 0], # length_slider.value
                {},     # length_slider.marks

                0,      # score_slider.min
                0,      # score_slider.max
                [0, 0], # score_slider.value
                {},     # score_slider.marks

                [],     # trips_list_2.options
                None,   # trips_list_2.value
                "https://israelhiking.osm.org.il/share/lXiAuFiwSa",
                html.Div("No Data Available", style={"color": "white"}),
            )

    # If we have a non-empty df, define some base references
    if not df.empty:
        min_length = float(df["Trail Length"].min())
        max_length = float(df["Trail Length"].max())
        min_score = float(df["Total Score"].min())
        max_score = float(df["Total Score"].max())

    # Ensure length_value and score_value are lists [low, high] and in correct range
    if not length_value or len(length_value) < 2:
        length_value = [min_length, max_length]
    else:
        # Clamp them if out of range
        length_value[0] = max(min_length, length_value[0])
        length_value[1] = min(max_length, length_value[1])

    if not score_value or len(score_value) < 2:
        score_value = [min_score, max_score]
    else:
        score_value[0] = max(min_score, score_value[0])
        score_value[1] = min(max_score, score_value[1])

    # Challenge mapping for "most challenging" logic
    challenge_mapping = {
        "Most Challenging": {
            "column": "Challenge",
            "rank_list": [
                "Very Challenging, with Lots of Obstacles in The Way",
                "There's Some Challenge, but Most of it is in Average Challenge",
                "There's some challenge, but Most of The Trail is Easy",
                "Medium Challenge",
                "Easy-Medium",
                "Easy",
                "No Challenge At All!"
            ],
            "display_name": "Challenge",
            "title": "Most Challenging"
        }
    }

    # Filter by selected range
    filtered_df = df[
        (df['Trail Length'] >= length_value[0]) & (df['Trail Length'] <= length_value[1]) &
        (df['Total Score'] >= score_value[0]) & (df['Total Score'] <= score_value[1])
    ].copy()

    # If after filtering there's nothing, handle gracefully
    if filtered_df.empty:
        return (
            [],             # Israel-map-layer
            "N/A",          # highest_score
            "N/A",          # mcv
            "N/A",          # mcd
            "N/A",          # mcta
            "0 Trips",      # check_trips
            "0 KM",         # average_length
            "0 Hours",      # average_time
            "N/A",          # mct
            min_length,     # length_slider.min
            max_length,     # length_slider.max
            length_value,   # length_slider.value
            {},            # length_slider.marks
            min_score,      
            max_score,      
            score_value,    
            {},            
            [],            # trips_list_2.options
            None,          # trips_list_2.value
            "https://israelhiking.osm.org.il/share/lXiAuFiwSa",
            html.Div("No Trips match the selected filters", style={"color": "white"}),
        )

    # Build markers for the map
    markers_israel = []
    for i, (coord, name) in enumerate(zip(filtered_df['Coordinates'], filtered_df['Trip'])):
        try:
            position = ast.literal_eval(coord)
            if isinstance(position, (list, tuple)) and len(position) == 2:
                markers_israel.append(
                    dl.Marker(
                        position=position,
                        children=[dl.Popup(name)],
                        id="israel-mark-" + str(i)
                    )
                )
        except (SyntaxError, ValueError):
            pass

    # Recompute card info for the filtered DF
    highest_score = filtered_df["Total Score"].max()
    trip_hs = filtered_df.loc[filtered_df["Total Score"] == highest_score, 'Trip'].iloc[0]
    common_view = filtered_df["View"].mode().iloc[0]
    common_distance = filtered_df["Distance"].mode().iloc[0]
    common_area = filtered_df["Area"].mode().iloc[0]
    check_trips = filtered_df["Trip"].nunique()
    avg_len = round(filtered_df["Trail Length"].mean(), 5)

    # Average walking time
    dur_list = filtered_df["Walking Hours"].tolist()
    whr_values = []
    for duration in dur_list:
        try:
            hours, minutes = map(int, duration.split(":"))
            whr_values.append(hours + minutes / 60)
        except:
            pass
    avg_time_int = sum(whr_values) / len(whr_values) if whr_values else 0
    avg_time = float_to_duration(avg_time_int)

    # Determine "most challenging trip"
    # We create a numerical rank if you have a more complex logic. For demonstration:
    if "Challenge" in filtered_df.columns:
        filtered_df["Challenge Rank"] = filtered_df["Challenge"].apply(
            lambda x: challenge_mapping["Most Challenging"]["rank_list"].index(x)
            if x in challenge_mapping["Most Challenging"]["rank_list"] else 999
        )
    else:
        filtered_df["Challenge Rank"] = 999

    # Sort to find top
    try:
        filtered_df_sorted = filtered_df.sort_values(
            by=["Challenge Rank", "Trail Length", "Incline Degree", "Decline Degree"],
            ascending=[True, False, False, True]
        )
        top_trip = filtered_df_sorted.iloc[0]["Trip"]
        top_incline_degree = filtered_df_sorted.iloc[0]["Incline Degree"]
    except IndexError:
        top_trip = "N/A"
        top_incline_degree = "N/A"

    # Build the slider marks
    length_marks = {}
    if min_length != max_length:
        length_marks = {
            int(min_length): {
                'label': f"{int(min_length)}",
                'style': {'font-size': '17px', 'font-weight': 'bold', 'color': '#333'}
            },
            int(max_length): {
                'label': f"{int(max_length)}",
                'style': {'font-size': '17px', 'font-weight': 'bold', 'color': '#333'}
            }
        }
    else:
        length_marks = {
            int(max_length): {
                'label': f"{int(max_length)}",
                'style': {'font-size': '17px', 'font-weight': 'bold', 'color': '#333'}
            }
        }

    score_marks = {}
    if min_score != max_score:
        score_marks = {
            int(min_score): {
                'label': f"{int(min_score)}",
                'style': {'font-size': '17px', 'font-weight': 'bold', 'color': '#333'}
            },
            int(max_score): {
                'label': f"{int(max_score)}",
                'style': {'font-size': '17px', 'font-weight': 'bold', 'color': '#333'}
            }
        }
    else:
        score_marks = {
            int(max_score): {
                'label': f"{int(max_score)}",
                'style': {'font-size': '17px', 'font-weight': 'bold', 'color': '#333'}
            }
        }

    # Build trip list for dropdown
    trips_options = [{'label': trip, 'value': trip} for trip in filtered_df["Trip"].unique()]
    # If the currently selected trip is still in the filtered set, keep it
    if trips_list_value in filtered_df["Trip"].values:
        trip_value = trips_list_value
    else:
        # If not, choose first or None
        trip_value = filtered_df["Trip"].values[0] if not filtered_df.empty else None

    # --------------- If triggered by the trip_picker --------------- #
    if triggered_id == "trip_picker":
        # The user explicitly picked a trip
        if not filtered_df.empty and trip_value in filtered_df["Trip"].values:
            row_details = filtered_df.loc[filtered_df["Trip"] == trip_value]
            if not row_details.empty:
                columns_to_show = [
                    "Trip",
                    "Area",
                    "Accessibility",
                    "Challenge",
                    "Terrain",
                    "View",
                    "Water",
                    "Walking Hours",
                    "Required Equipment",
                    "Season",
                    "Entry Fee",
                    "Distance",
                    "Total Score",
                ]
                columns_in_df = [col for col in columns_to_show if col in row_details.columns]
                row_subset = row_details[columns_in_df]
                # Transpose
                row_subset_t = row_subset.T
                row_subset_t.columns = ["Value"]
                row_subset_t["Attribute"] = row_subset_t.index
                row_subset_t = row_subset_t.reset_index(drop=True)
                row_subset_t = row_subset_t[["Attribute", "Value"]]
                rows_dicts = row_subset_t.to_dict("records")

                details_table = dbc.Table(
                    [
                        html.Thead(html.Tr([html.Th("Attribute"), html.Th("Value")])),
                        html.Tbody([
                            html.Tr([html.Td(r["Attribute"]), html.Td(r["Value"])]) 
                            for r in rows_dicts
                        ]),
                    ],
                    bordered=True,
                    hover=True,
                    striped=True,
                    responsive=True,
                    style={"backgroundColor": "white", "color": "black"},
                )
            else:
                details_table = html.Div("No trip found.")

            # Update iFrame
            link_trail_src = row_details["Trail Link"].iloc[0] if "Trail Link" in row_details.columns else ""

            trip_details_div = html.Div(
                [
                    html.H3("Selected Trip Details", style={"color": "black"}),
                    details_table,
                ],
                style={
                    "backgroundColor": "",
                    "padding": "2px",
                    "border": "1px solid #444",
                    "borderRadius": "5px",
                    "font-size":"18px",
                    "opacity": "100%",
                },
            )

            return (
                markers_israel,
                f"{trip_hs} : {highest_score}",
                f"{common_view}",
                f"{common_distance}",
                f"{common_area}",
                f"{check_trips} Trips",
                f"{avg_len} KM",
                f"{avg_time} Hours",
                f"{top_trip}: {top_incline_degree}° Average",
                min_length,
                max_length,
                length_value,
                length_marks,
                min_score,
                max_score,
                score_value,
                score_marks,
                trips_options,
                trip_value,  # keep selection
                link_trail_src,
                trip_details_div,
            )
        else:
            # Trip not found in the filtered set
            return (
                markers_israel,
                f"{trip_hs} : {highest_score}",
                f"{common_view}",
                f"{common_distance}",
                f"{common_area}",
                f"{check_trips} Trips",
                f"{avg_len} KM",
                f"{avg_time} Hours",
                f"{top_trip}: {top_incline_degree}° Average",
                min_length,
                max_length,
                length_value,
                length_marks,
                min_score,
                max_score,
                score_value,
                score_marks,
                trips_options,
                trip_value,
                "https://israelhiking.osm.org.il/share/lXiAuFiwSa",
                html.Div(
                    "No trip selected.",
                    style={"color": "white", "fontSize": "16px", "fontWeight": "bold"},
                ),
            )
            
    elif triggered_id == "update_db2":
        df = load_data_from_gsheet()
        df["Trail Length"] = pd.to_numeric(df["Trail Length"], errors="coerce")
        # Drop rows with invalid or missing "Trail Length" values
        df = df.dropna(subset=["Trail Length"])

        # Convert other necessary columns to numeric if they exist
        numeric_columns = ["Total Score", "Incline Degree", "Decline Degree"]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        # Drop rows with invalid or missing values in these columns if necessary
        df = df.dropna(subset=["Total Score", "Incline Degree", "Decline Degree"])
        if df.empty:
            return (
                [],                     # Israel-map-layer (no markers)
                "",                     # highest_score
                "",                     # mcv
                "",                     # mcd
                "",                     # mcta
                "0 Trips",             # check_trips
                "0 KM",                # average_length
                "0 Hours",             # average_time
                "N/A",                 # mct

                0,                     # length_slider.min
                0,                     # length_slider.max
                [0, 0],                # length_slider.value
                {},                    # length_slider.marks

                0,                     # score_slider.min
                0,                     # score_slider.max
                [0, 0],                # score_slider.value
                {},                    # score_slider.marks

                [],                    # trips_list_2.options
                None,                  # trips_list_2.value
                "https://israelhiking.osm.org.il/share/lXiAuFiwSa",  # picked_trail_map.src
                html.Div("No Data Available", style={"color": "white"}),
            )
        min_length = float(df["Trail Length"].min())
        max_length = float(df["Trail Length"].max())
        min_score = float(df["Total Score"].min())
        max_score = float(df["Total Score"].max())
        if not length_value or len(length_value) < 2:
            length_value = [min_length, max_length]
        else:
            length_value[0] = max(min_length, length_value[0])
            length_value[1] = min(max_length, length_value[1])

        if not score_value or len(score_value) < 2:
            score_value = [min_score, max_score]
        else:
            score_value[0] = max(min_score, score_value[0])
            score_value[1] = min(max_score, score_value[1])

        filtered_df = df[
            (df["Trail Length"] >= length_value[0]) & 
            (df["Trail Length"] <= length_value[1]) &
            (df["Total Score"]   >= score_value[0])   & 
            (df["Total Score"]   <= score_value[1])
        ].copy()

        if filtered_df.empty:
            return (
                [],                    # Israel-map-layer
                "N/A",                # highest_score
                "N/A",                # mcv
                "N/A",                # mcd
                "N/A",                # mcta
                "0 Trips",            # check_trips
                "0 KM",               # average_length
                "0 Hours",            # average_time
                "N/A",                # mct
                min_length,           # length_slider.min
                max_length,           # length_slider.max
                [min_length, max_length],  # length_slider.value
                {},                   # length_slider.marks
                min_score, 
                max_score, 
                [min_score, max_score],
                {},                   # score_slider.marks
                [],                   # trips_list_2.options
                None,                 # trips_list_2.value
                "https://israelhiking.osm.org.il/share/lXiAuFiwSa",
                html.Div("No Trips match the selected filters", style={"color": "white"}),
            )

        markers_israel = []
        for i, (coord, name) in enumerate(zip(filtered_df['Coordinates'], filtered_df['Trip'])):
            try:
                position = ast.literal_eval(coord)  # parse "[lat, lon]" string
                if isinstance(position, (list, tuple)) and len(position) == 2:
                    markers_israel.append(
                        dl.Marker(
                            position=position,
                            children=[dl.Popup(name)],
                            id="israel-mark-" + str(i)
                        )
                    )
            except (SyntaxError, ValueError):
                pass

        highest_score = filtered_df["Total Score"].max()
        trip_hs = filtered_df.loc[filtered_df["Total Score"] == highest_score, 'Trip'].iloc[0]
        common_view = filtered_df["View"].mode().iloc[0]
        common_distance = filtered_df["Distance"].mode().iloc[0]
        common_area = filtered_df["Area"].mode().iloc[0]
        check_trips = filtered_df["Trip"].nunique()
        avg_len = round(filtered_df["Trail Length"].mean(), 5)

        dur_list = filtered_df["Walking Hours"].tolist()
        whr_values = []
        for duration in dur_list:
            try:
                hours, minutes = map(int, duration.split(":"))
                whr_values.append(hours + minutes / 60)
            except:
                pass
        avg_time_int = sum(whr_values) / len(whr_values) if whr_values else 0
        avg_time = float_to_duration(avg_time_int)

        if "Challenge" in filtered_df.columns:
            # A user-defined ranking approach
            rank_list = [
                "Very Challenging, with Lots of Obstacles in The Way",
                "There's Some Challenge, but Most of it is in Average Challenge",
                "There's some challenge, but Most of The Trail is Easy",
                "Medium Challenge",
                "Easy-Medium",
                "Easy",
                "No Challenge At All!"
            ]
            filtered_df["Challenge Rank"] = filtered_df["Challenge"].apply(
                lambda x: rank_list.index(x) if x in rank_list else 999
            )
        else:
            filtered_df["Challenge Rank"] = 999

        filtered_df_sorted = filtered_df.sort_values(
            by=["Challenge Rank", "Trail Length", "Incline Degree", "Decline Degree"],
            ascending=[True, False, False, True]
        )
        top_trip = filtered_df_sorted.iloc[0]["Trip"]
        top_incline_degree = filtered_df_sorted.iloc[0]["Incline Degree"]

        length_marks = {}
        if min_length != max_length:
            length_marks = {
                int(min_length): {"label": f"{int(min_length)}", "style": {"font-size": "17px", "font-weight": "bold", "color": "#333"}},
                int(max_length): {"label": f"{int(max_length)}", "style": {"font-size": "17px", "font-weight": "bold", "color": "#333"}}
            }
        else:
            length_marks = {
                int(max_length): {"label": f"{int(max_length)}", "style": {"font-size": "17px", "font-weight": "bold", "color": "#333"}}
            }

        score_marks = {}
        if min_score != max_score:
            score_marks = {
                int(min_score): {"label": f"{int(min_score)}", "style": {"font-size": "17px", "font-weight": "bold", "color": "#333"}},
                int(max_score): {"label": f"{int(max_score)}", "style": {"font-size": "17px", "font-weight": "bold", "color": "#333"}}
            }
        else:
            score_marks = {
                int(max_score): {"label": f"{int(max_score)}", "style": {"font-size": "17px", "font-weight": "bold", "color": "#333"}}
            }

        trips_options = [{'label': trip, 'value': trip} for trip in filtered_df["Trip"].unique()]
        # If the currently selected trip is still in the filtered set, keep it
        if trips_list_value in filtered_df["Trip"].values:
            trip_value = trips_list_value
        else:
            trip_value = filtered_df["Trip"].values[0] if not filtered_df.empty else None

        # ---------------------------------------------------------
        link_trail_src = "https://israelhiking.osm.org.il/share/lXiAuFiwSa"
        trip_details_div = html.Div(
            "No trip selected.",
            style={"color": "white", "fontSize": "16px", "fontWeight": "bold"},
        )

        return (
            markers_israel,                            # Israel-map-layer
            f"{trip_hs} : {highest_score}",            # highest_score
            f"{common_view}",                          # mcv
            f"{common_distance}",                      # mcd
            f"{common_area}",                          # mcta
            f"{check_trips} Trips",                    # check_trips
            f"{avg_len} KM",                           # average_length
            f"{avg_time} Hours",                       # average_time
            f"{top_trip}: {top_incline_degree}° Average",  # mct

            min_length,                                # length_slider.min
            max_length,                                # length_slider.max
            [length_value[0], length_value[1]],        # length_slider.value
            length_marks,                              # length_slider.marks

            min_score,                                 # score_slider.min
            max_score,                                 # score_slider.max
            [score_value[0], score_value[1]],          # score_slider.value
            score_marks,                               # score_slider.marks

            trips_options,                             # trips_list_2.options
            trip_value,                                # trips_list_2.value
            link_trail_src,                            # picked_trail_map.src
            trip_details_div                           # trip_details
        )
        
    elif triggered_id == 'filt_res':
        df["Trail Length"] = pd.to_numeric(df["Trail Length"], errors="coerce")
        df = df.dropna(subset=["Trail Length"])

        numeric_columns = ["Total Score", "Incline Degree", "Decline Degree"]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=numeric_columns)

        if df.empty:
            return (
                [],                     # Israel-map-layer
                "",                     # highest_score
                "",                     # mcv
                "",                     # mcd
                "",                     # mcta
                "0 Trips",             # check_trips
                "0 KM",                # average_length
                "0 Hours",             # average_time
                "N/A",                 # mct

                0,                     # length_slider.min
                0,                     # length_slider.max
                [0, 0],                # length_slider.value
                {},                    # length_slider.marks

                0,                     # score_slider.min
                0,                     # score_slider.max
                [0, 0],                # score_slider.value
                {},                    # score_slider.marks

                [],                    # trips_list_2.options
                None,                  # trips_list_2.value
                "https://israelhiking.osm.org.il/share/lXiAuFiwSa",
                html.Div("No Data Available", style={"color": "white"}),
            )
        min_length = float(df["Trail Length"].min())
        max_length = float(df["Trail Length"].max())
        min_score = float(df["Total Score"].min())
        max_score = float(df["Total Score"].max())

        length_value = [min_length, max_length]  # full length range
        score_value = [min_score, max_score]     # full score range
        trip_value = None                        # no trip selected

        filtered_df = df.copy()  # same as entire dataset now
        if filtered_df.empty:
            return (
                [],                    
                "N/A",                
                "N/A",                
                "N/A",                
                "N/A",                
                "0 Trips",            
                "0 KM",               
                "0 Hours",            
                "N/A",                
                min_length,           
                max_length,           
                [min_length, max_length],
                {},                   
                min_score,            
                max_score,            
                [min_score, max_score],
                {},                   
                [],
                None,
                "https://israelhiking.osm.org.il/share/lXiAuFiwSa",
                html.Div("No Trips match the selected filters", style={"color": "white"}),
            )

        markers_israel = []
        for i, (coord, name) in enumerate(zip(filtered_df['Coordinates'], filtered_df['Trip'])):
            try:
                position = ast.literal_eval(coord)
                if isinstance(position, (list, tuple)) and len(position) == 2:
                    markers_israel.append(
                        dl.Marker(
                            position=position,
                            children=[dl.Popup(name)],
                            id="israel-mark-" + str(i)
                        )
                    )
            except:
                pass

        highest_score = filtered_df["Total Score"].max()
        trip_hs = filtered_df.loc[filtered_df["Total Score"] == highest_score, 'Trip'].iloc[0]
        common_view = filtered_df["View"].mode().iloc[0]
        common_distance = filtered_df["Distance"].mode().iloc[0]
        common_area = filtered_df["Area"].mode().iloc[0]
        check_trips = filtered_df["Trip"].nunique()
        avg_len = round(filtered_df["Trail Length"].mean(), 5)

        # average walking time
        dur_list = filtered_df["Walking Hours"].tolist()
        whr_values = []
        for duration in dur_list:
            try:
                hours, minutes = map(int, duration.split(":"))
                whr_values.append(hours + minutes / 60)
            except:
                pass
        avg_time_int = sum(whr_values) / len(whr_values) if whr_values else 0
        avg_time = float_to_duration(avg_time_int)

        # -----------------------------------------------------------------
        # 9) "Most challenging trip" logic
        # -----------------------------------------------------------------
        if "Challenge" in filtered_df.columns:
            rank_list = [
                "Very Challenging, with Lots of Obstacles in The Way",
                "There's Some Challenge, but Most of it is in Average Challenge",
                "There's some challenge, but Most of The Trail is Easy",
                "Medium Challenge",
                "Easy-Medium",
                "Easy",
                "No Challenge At All!"
            ]
            filtered_df["Challenge Rank"] = filtered_df["Challenge"].apply(
                lambda x: rank_list.index(x) if x in rank_list else 999
            )
        else:
            filtered_df["Challenge Rank"] = 999

        filtered_df_sorted = filtered_df.sort_values(
            by=["Challenge Rank", "Trail Length", "Incline Degree", "Decline Degree"],
            ascending=[True, False, False, True]
        )
        top_trip = filtered_df_sorted.iloc[0]["Trip"]
        top_incline_degree = filtered_df_sorted.iloc[0]["Incline Degree"]

        length_marks = {}
        if min_length != max_length:
            length_marks = {
                int(min_length): {
                    'label': f"{int(min_length)}",
                    'style': {'font-size': '17px', 'font-weight': 'bold', 'color': '#333'}
                },
                int(max_length): {
                    'label': f"{int(max_length)}",
                    'style': {'font-size': '17px', 'font-weight': 'bold', 'color': '#333'}
                }
            }
        else:
            length_marks = {
                int(max_length): {
                    'label': f"{int(max_length)}",
                    'style': {'font-size': '17px', 'font-weight': 'bold', 'color': '#333'}
                }
            }

        score_marks = {}
        if min_score != max_score:
            score_marks = {
                int(min_score): {
                    'label': f"{int(min_score)}",
                    'style': {'font-size': '17px', 'font-weight': 'bold', 'color': '#333'}
                },
                int(max_score): {
                    'label': f"{int(max_score)}",
                    'style': {'font-size': '17px', 'font-weight': 'bold', 'color': '#333'}
                }
            }
        else:
            score_marks = {
                int(max_score): {
                    'label': f"{int(max_score)}",
                    'style': {'font-size': '17px', 'font-weight': 'bold', 'color': '#333'}
                }
            }

        trips_options = [{'label': trip, 'value': trip} for trip in filtered_df["Trip"].unique()]

        link_trail_src = ""
        trip_details_div = html.Div(
            "No trip selected.",
            style={"color": "white", "fontSize": "16px", "fontWeight": "bold"},
        )

        return (
            markers_israel,                            # Israel-map-layer
            f"{trip_hs} : {highest_score}",            # highest_score
            f"{common_view}",                          # mcv
            f"{common_distance}",                      # mcd
            f"{common_area}",                          # mcta
            f"{check_trips} Trips",                    # check_trips
            f"{avg_len} KM",                           # average_length
            f"{avg_time} Hours",                       # average_time
            f"{top_trip}: {top_incline_degree}° Average",  # mct

            min_length,                                # length_slider.min
            max_length,                                # length_slider.max
            [length_value[0], length_value[1]],        # length_slider.value
            length_marks,                              # length_slider.marks

            min_score,                                 # score_slider.min
            max_score,                                 # score_slider.max
            [score_value[0], score_value[1]],          # score_slider.value
            score_marks,                               # score_slider.marks

            trips_options,                             # trips_list_2.options
            trip_value,                                # trips_list_2.value
            link_trail_src,                            # picked_trail_map.src
            trip_details_div                           # trip_details
        )
    else:
        
        score_value = dash.no_update
        length_value = dash.no_update

        # We basically just return the updated states
        return (
            markers_israel,                            # Israel-map-layer
            f"{trip_hs} : {highest_score}",             # highest_score
            f"{common_view}",                          # mcv
            f"{common_distance}",                      # mcd
            f"{common_area}",                          # mcta
            f"{check_trips} Trips",                    # check_trips
            f"{avg_len} KM",                           # average_length
            f"{avg_time} Hours",                       # average_time
            f"{top_trip}: {top_incline_degree}° Average",  # mct

            min_length,                                # length_slider.min
            max_length,                                # length_slider.max
            length_value,                              # length_slider.value
            length_marks,                              # length_slider.marks

            min_score,                                 # score_slider.min
            max_score,                                 # score_slider.max
            score_value,                               # score_slider.value
            score_marks,                               # score_slider.marks

            trips_options,                             # trips_list_2.options
            trip_value,                                # trips_list_2.value
            link_trail_src,                            # picked_trail_map.src
            trip_details_div                           # trip_details
        )



def tab2_layout():
    df1=df_global.copy()
    trip_options = df1["Trip"].unique().tolist() if not df1.empty else []
    trip_count = df1["Trip"].nunique() if not df1.empty else 0

        
    return html.Div(
        style=background_style,
        children=[
            dcc.Store(id='df-store', data=df1.to_dict("records")),
            dcc.Store(id='default-values', data={
                'trip': "",
                'mid_trail_coordinate': "",
                "trail_link": "",
                'area_scores': "Golan Heights - North-East Galilee",
                'Accessibility': "Open to All",
                'Season': "Spring",
                'Challenge': "Very Challenging, with Lots of Obstacles in The Way",
                'terrain': "Mountainous region with lots of rivers and creeks",
                'view': "Vivid green mountains, lots of streams, and rocks",
                'shade': "Mostly shaded, cooled and glimpses of sunshine occasionally",
                'Entry_Fee': "Free of charge",
                'water': "Lots of water, with several entrances, easy access",
                'nearby_attractions': "Full of attractions nearby: wineries, viewpoints, food, pubs and resorts",
                'required_eq': "Only a small bag with 1.5 liter bottle. hat, casual clothing",
                'circular': "",
                'trail_length': "",
                'incline': "",
                'decline': "",
                'percentagein': "",
                'percentagede': "",
                'inclinedg': "",
                'declinedg': "",
                'kmh': "",
                'walkinghr': "",
                'how_far_from_me': "Half an hour drive",
                'weather': "Clear, an average of 18-20C",
                'crowdness': "Not crowded at all"
            }),

            dbc.Container(
                style=container_style,
                children=[
                    html.H1("Trip Evaluation", style=heading_style),
                    html.Hr(),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H5("Name & Location"),
                                    dbc.Label("Trip Name:"),
                                    dcc.Input(id='trip_name', type='text', value="", className="form-control"),
                                    dbc.Label("Coordinate:"),
                                    dcc.Input(id='coordinate', type='text', value="", className="form-control"),
                                    html.Br(),
                                    dbc.Label("Trail Link:"),
                                    dcc.Input(id='trail_link', type='text', value="", className="form-control"),
                                    html.Br(),
                                    dbc.Label("Travel Area:"),
                                    dcc.Dropdown(
                                        id='area',
                                        options=[{'label': k, 'value': k} for k in area_scores.keys()],
                                        value="Golan Heights - North-East Galilee",
                                        className="form-control"
                                    ),
                                    html.Br(),
                                    dbc.Label("Accessibility:"),
                                    dcc.Dropdown(
                                        id='accessibility',
                                        options=[{'label': k, 'value': k} for k in Accessibility.keys()],
                                        value="Open to All",
                                        className="form-control"
                                    ),
                                    html.Br(),
                                    dbc.Label("Travelled Season:"),
                                    dcc.Dropdown(
                                        id='Season',
                                        options=[{'label': k, 'value': k} for k in Season.keys()],
                                        value="Spring",
                                        className="form-control"
                                                            ),
                                    dcc.Markdown(
                                        id='trips_count',
                                        children=f"### Trips Evaluation Count\nThere are **{trip_count}** trips.",
                                        style={'fontSize': '24px', 'marginTop': '20px'}
                                    ),
                                    dbc.Button("Update DB", id='update-btn', color='primary', n_clicks=0, style=button_style_11),

                                    html.Br(),
                                    dcc.Markdown(
                                        id='Remove_trip',
                                        children="### Remove a trip",
                                        style={'fontSize': '24px', 'marginTop': '20px', 'textAlign': 'left'}
                                    ),
                                    dcc.Dropdown(
                                        id='trips_list',
                                        options=trip_options,
                                        value=df_global['Trip'].iloc[0],
                                        className="form-control"
                                    ),
                                    dbc.Button("Remove", id='remove_btn', color='success', n_clicks=0, style=button_style3),
                                    dcc.ConfirmDialog(
                                        id='confirm_remove_trip',
                                        message="Are you sure you want to remove this trip? This action cannot be undone.",
                                    ),
                                ],
                                width=3
                            ),
                            dbc.Col(
                                [
                                    html.H5("Trail Features"),
                                    dbc.Label("Challenge:"),
                                    dcc.Dropdown(
                                        id='challenge',
                                        options=[{'label': c, 'value': c} for c in Challenge.keys()],
                                        value="Very Challenging, with Lots of Obstacles in The Way",
                                        className="form-control"
                                    ),
                                    html.Br(),
                                    dbc.Label("Terrain:"),
                                    dcc.Dropdown(
                                        id='terrain',
                                        options=[{'label': k, 'value': k} for k in Terrain.keys()],
                                        value="Mountainous region with lots of rivers and creeks",
                                        className="form-control"
                                    ),
                                    html.Br(),
                                    dbc.Label("View:"),
                                    dcc.Dropdown(
                                        id='view',
                                        options=[{'label': k, 'value': k} for k in View.keys()],
                                        value="Vivid green mountains, lots of streams, and rocks",
                                        className="form-control"
                                    ),
                                    html.Br(),
                                    dbc.Label("How Shaded?"),
                                    dcc.Dropdown(
                                        id='shade',
                                        options=[{'label': k, 'value': k} for k in Shade.keys()],
                                        value="Mostly shaded, cooled and glimpses of sunshine occasionally",
                                        className="form-control"
                                    ),
                                    html.Br(),
                                    dbc.Label("Water:"),
                                    dcc.Dropdown(
                                        id='water',
                                        options=[{'label': k, 'value': k} for k in Water.keys()],
                                        value="Lots of water, with several entrances, easy access",
                                        className="form-control"
                                    ),
                                    html.Br(),
                                    dbc.Label("Required Equipment:"),
                                    dcc.Dropdown(
                                        id='required_eq',
                                        options=[{'label': k, 'value': k} for k in Required_eq.keys()],
                                        value="Only a small bag with 1.5 liter bottle. hat, casual clothing",
                                        className="form-control"
                                    ),
                                    html.Br(),
                                    dbc.Col(
                                        [
                                            dbc.Label("Is It Circular?"),
                                            html.Br(),
                                            dcc.Dropdown(
                                                id='circular',
                                                options=[{'label': k, 'value': k} for k in circular.keys()],
                                                value="",
                                                className="form-control"
                                            ),
                                            html.Div([
                                                html.Br(),
                                                dbc.Label("Trail Length:"),
                                                dcc.Input(id='trail_length', type='text', value="", className="form-control"),
                                                html.Br(),
                                                dbc.Label("Elevation:", style={'justify-content': 'center'}),
                                                html.Br(),
                                                html.Div([
                                                    dbc.Label("Up:", style={"margin-right": "10px"}),
                                                    dcc.Input(id='incline', type='text', value="",
                                                              className="form-control",
                                                              style={"display": "inline-block", "width": "45%"},
                                                              disabled=True),
                                                    dbc.Label("Down:", style={"margin-left": "20px", "margin-right": "10px"}),
                                                    dcc.Input(id='decline', type='text', value="",
                                                              className="form-control",
                                                              style={"display": "inline-block", "width": "45%"},
                                                              disabled=True)
                                                ], style={"display": "flex", "align-items": "center", "justify-content": "space-between"}),
                                                html.Br(),
                                                html.Div([
                                                    dcc.Input(id='percentagein', type='text', value="",
                                                              className="form-control",
                                                              style={"display": "inline-block", "width": "45%", "margin-left": "30px"},
                                                              disabled=True),
                                                    dbc.Label("%:", style={"margin-left": "10px", "margin-right": "10px"}),
                                                    dcc.Input(id='percentagede', type='text', value="",
                                                              className="form-control",
                                                              style={"display": "inline-block", "width": "45%", "margin-left": "30px"},
                                                              disabled=True),
                                                    dbc.Label("%:", style={"margin-left": "10px"})
                                                ], style={"display": "flex", "align-items": "center", "justify-content": "space-between"}),
                                                html.Br(),
                                                html.Div([
                                                    dcc.Input(id='inclinedg', type='text', value="",
                                                              className="form-control",
                                                              style={"display": "inline-block", "width": "65%", "margin-left": "30px"},
                                                              disabled=True),
                                                    dbc.Label("°", style={"margin-left": "10px", "margin-right": "10px"}),
                                                    dcc.Input(id='declinedg', type='text', value="",
                                                              className="form-control",
                                                              style={"display": "inline-block", "width": "65%", "margin-left": "30px"},
                                                              disabled=True),
                                                    dbc.Label("°", style={"margin-left": "10px", "margin-right": "10px"})
                                                ], style={"display": "flex", "align-items": "center", "justify-content": "space-between"}),
                                            ]),
                                            html.Br(),
                                            dbc.Label("Estimated Travel Time:"),
                                            html.Br(),
                                            dbc.Label("Enter your average km/h speed:"),
                                            dcc.Input(id='kmh', type='text', value="",
                                                      className="form-control",
                                                      style={"display": "inline-block", "width": "45%"}),
                                            dbc.Label("KM/H", style={"margin-left": "10px"}),
                                            html.Br(),
                                            dcc.Input(id='walkinghr', type='text', value="",
                                                      className="form-control",
                                                      style={"display": "inline-block", "width": "45%"},
                                                      disabled=True),
                                            dbc.Label("Hours", style={"margin-left": "10px", "margin-right": "10px"})
                                        ],
                                        width=6
                                    ),
                                ],
                                width=4
                            ),
                            dbc.Col(
                                [
                                    html.H5("General Conditions"),
                                    dbc.Label("Weather:"),
                                    dcc.Dropdown(
                                        id='weather',
                                        options=[{'label': k, 'value': k} for k in Weather.keys()],
                                        value="Clear, an average of 18-20C",
                                        className="form-control"
                                    ),
                                    html.Br(),
                                    dbc.Label("Crowdness:"),
                                    dcc.Dropdown(
                                        id='crowdness',
                                        options=[{'label': k, 'value': k} for k in Crowdness.keys()],
                                        value="Not crowded at all",
                                        className="form-control"
                                    ),
                                    html.Br(),
                                    dbc.Label("Nearby Attractions:"),
                                    dcc.Dropdown(
                                        id='nearby',
                                        options=[{'label': k, 'value': k} for k in Nearby_attractions.keys()],
                                        value="Full of attractions nearby: wineries, viewpoints, food, pubs and resorts",
                                        className="form-control"
                                    ),
                                    html.Br(),
                                    dbc.Label("Entry Fee:"),
                                    dcc.Dropdown(
                                        id='Entry_Fee',
                                        options=[{'label': k, 'value': k} for k in Entry_Fee.keys()],
                                        value="Free of charge",
                                        className="form-control"
                                    ),
                                    html.Br(),
                                    dbc.Label("How Far Is It?"),
                                    dcc.Dropdown(
                                        id='how_far_from_me',
                                        options=[{'label': k, 'value': k} for k in How_far_from_me.keys()],
                                        value="Half an hour drive",
                                        className="form-control"
                                    ),

                                    html.Br(),
                                    dbc.Button("Calculate Score", id='calculate-btn', color='primary', n_clicks=0, style=button_style),
                                    dbc.Button("Remove DataFrame", id='reset-btn', color='primary', n_clicks=0, style=button_style_2),
                                    dcc.ConfirmDialog(
                                        id='confirm_reset',
                                        message="Are you sure you want to clear the DataFrame? This action cannot be undone.",
                                    ),
                                    dbc.Modal(
                                        [
                                            dbc.ModalHeader("Trip Score"),
                                            dbc.ModalBody(id="modal-body"),
                                        ],
                                        id="score-modal",
                                        is_open=False,
                                    ),
                                ],
                                width=4,
                            ),
                        ]
                    ),
                ]
            ),
        ]
    )

app.layout = tab1_layout()

# ---------------------------------------------------------------------------------
#   Callback
# ---------------------------------------------------------------------------------
@app.callback(
    [
        Output("modal-body", "children"),
        Output("score-modal", "is_open"),
        Output("confirm_reset", "displayed"),
        Output('trips_count', 'children'),
        Output("confirm_remove_trip", "displayed"),
        Output("trips_list", "options"),
        Output("trips_list", "value"),
        Output("trip_name", "value"),
        Output("coordinate", "value"),
        Output("trail_link", "value"),
        Output("area", "value"),
        Output("accessibility", "value"),
        Output("Season", "value"),
        Output("challenge", "value"),
        Output("terrain", "value"),
        Output("view", "value"),
        Output("shade", "value"),
        Output("water", "value"),
        Output("trail_length", "value"),
        Output("circular", "value"),
        Output("required_eq", "value"),
        Output("weather", "value"),
        Output("crowdness", "value"),
        Output("nearby", "value"),
        Output("Entry_Fee", "value"),
        Output("how_far_from_me", "value"),
        Output("kmh", "value"),
        Output('incline', 'disabled'),
        Output('decline', 'disabled'),
        Output('percentagein', 'disabled'),
        Output('percentagede', 'disabled'),
        Output("walkinghr", "disabled"),
        Output("decline", "value"),
        Output("declinedg", "value"),
        Output("inclinedg", "value"),
        Output("percentagein", "value"),
        Output("percentagede", "value"),
        Output("walkinghr", "value"),
        Output('df-store', 'data'),

    ],
    [
        Input("calculate-btn", "n_clicks"),
        Input('circular', 'value'),
        Input("confirm_remove_trip", "submit_n_clicks"),
        Input("remove_btn", "n_clicks"),
        Input("confirm_reset", "submit_n_clicks"),
        Input('update-btn','n_clicks'),
        Input("reset-btn", "n_clicks"),
        Input("incline", "value"),
        Input("decline", "value"),
        Input("percentagein", "value"),
        Input("kmh", "value")
    ],
    [
        State("trip_name", "value"),
        State("coordinate", "value"),
        State("trail_link", "value"),
        State("area", "value"),
        State("accessibility", "value"),
        State("Season", "value"),
        State("challenge", "value"),
        State("terrain", "value"),
        State("view", "value"),
        State("shade", "value"),
        State("water", "value"),
        State("required_eq", "value"),
        State("circular", "value"),
        State("trail_length", "value"),
        State("incline", "value"),
        State("decline", "value"),
        State("inclinedg", "value"),
        State("declinedg", "value"),
        State("percentagein", "value"),
        State("percentagede", "value"),
        State("kmh", "value"),
        State("walkinghr", "value"),
        State("weather", "value"),
        State("crowdness", "value"),
        State("nearby", "value"),
        State("Entry_Fee", "value"),
        State("how_far_from_me", "value"),
        State("trips_list", "value"),
        State("default-values", "data"),
    ],
    prevent_initial_call=True,
)
def update_tab2(
    calculate_clicks, circular_input, confirm_remove_trip, remove_clicks, update_clicks, confirm_reset,
    reset_clicks, incline_value, decline_input, precentagein_input, kmh_input,
    trip_name, coordinate, trail_link, area, accessibility, season, challenge, terrain, view, shade,
    water, required_eq, circular_val, trail_length, inc, dec, incdeg, decdeg, incpre, decpre,
    kmh, walkinghours, weather, crowdness, nearby, entry_fee, how_far_from_me, trips_list_value, defaults
):

    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    # Initialize return variables
    trip_count_content = dash.no_update
    modal_content = dash.no_update
    modal_is_open = dash.no_update
    confirm_remove_trip_displayed = False
    confirm_reset_displayed = False
    trips_options = dash.no_update
    trip_value = dash.no_update

    incline_disabled = dash.no_update
    decline_disabled = dash.no_update
    decline_output = dash.no_update
    inclinedg_value = dash.no_update
    declinedg_value = dash.no_update
    percentagein_disabled = dash.no_update
    percentagede_disabled = dash.no_update
    whr_disabled = dash.no_update
    percentagein_value = dash.no_update
    percentagede_value = dash.no_update
    walkinghr_value = dash.no_update

    # Reload from GSheets to keep data fresh
    df = df_global.copy()

    # Update the trips dropdown
    if not df.empty and "Trip" in df.columns:
        trips_list = df["Trip"].unique().tolist()
        trips_options = [{'label': t, 'value': t} for t in trips_list]
        if trips_list:
            if trips_list_value in trips_list:
                trip_value = trips_list_value
            else:
                trip_value = trips_list[0]
        else:
            trip_value = None
    else:
        trips_options = []
        trip_value = None

    # Update trip count
    valid_score_count = df["Trip"].nunique()
    trip_count_content = f"""
    ### Trips Evaluation Count
    There are **{valid_score_count}** trips.
    """

    # Handle circular logic
    if circular_input == "Yes":
        # If "Yes" => incline possible, decline = negative incline, etc.
        incline_disabled = False
        decline_disabled = True
        percentagein_disabled = True
        percentagede_disabled = True
        whr_disabled = True

        # If user typed something in 'incline'
        if incline_value not in [None, ""]:
            try:
                incline_value_num = float(incline_value)
                decline_output = 0 + incline_value_num
                decs_value = float(decline_output)

                percentagein_value = 50
                percentagede_value = 50

                # If we also have a valid trail_length => calculate degrees + Naismith
                try:
                    if trail_length not in [None, ""]:
                        trail_length_num = float(trail_length)
                        # half the distance is up, half is down
                        initial_cal = math.atan(incline_value_num / (trail_length_num * 1000 / 2))
                        deg_val = round(math.degrees(initial_cal), 4)
                        inclinedg_value = deg_val
                        declinedg_value = -deg_val

                        if kmh_input not in [None, ""]:
                            v_kmh = float(kmh_input)
                            walkinghr_value = naismith_rule(trail_length_num, incline_value_num, decs_value, v_kmh)
                        else:
                            walkinghr_value = dash.no_update
                except ValueError:
                    # invalid float for trail length
                    pass
            except ValueError:
                # invalid float for incline
                decline_output = ""
        else:
            decline_output = ""

    elif circular_input == "No":
        # If "No" => both incline & decline enabled, plus we can assign partial distances
        incline_disabled = False
        decline_disabled = False
        percentagein_disabled = False
        percentagede_disabled = False
        whr_disabled = True

        # Recompute percentages
        if precentagein_input not in [None, ""]:
            try:
                percentagein_num = float(precentagein_input)
                percentagein_value = percentagein_num
                percentagede_value = 100 - percentagein_num
            except ValueError:
                percentagein_value = ""
                percentagede_value = ""
        else:
            percentagein_value = ""
            percentagede_value = ""

        # If we have a valid trail_length => compute degrees
        try:
            if trail_length not in [None, ""]:
                trail_length_num = float(trail_length)

                # Up
                if incline_value not in [None, ""]:
                    inc_val_num = float(incline_value)
                    pin_val = float(percentagein_value) if percentagein_value not in ["", None] else 0
                    if pin_val > 0:
                        initial_cal_up = math.atan(inc_val_num / (trail_length_num * 1000 * (pin_val / 100)))
                    else:
                        initial_cal_up = 0
                    inclinedg_value = round(math.degrees(initial_cal_up), 4)

                # Down
                if decline_input not in [None, ""]:
                    dec_val_num = float(decline_input)
                    pde_val = float(percentagede_value) if percentagede_value not in ["", None] else 0
                    if pde_val > 0:
                        initial_cal_down = math.atan(dec_val_num / (trail_length_num * 1000 * (pde_val / 100)))
                    else:
                        initial_cal_down = 0
                    declinedg_value = round(math.degrees(initial_cal_down), 4)

                # If we have valid up/down & kmh => compute Naismith
                if (incline_value not in [None, ""] and decline_input not in [None, ""]) and kmh_input not in [None, ""]:
                    inc_val_num = float(incline_value)
                    dec_val_num = -float(decline_input)
                    v_kmh = float(kmh_input)
                    walkinghr_value = naismith_rule(trail_length_num, inc_val_num, dec_val_num, v_kmh)
        except ValueError:
            # invalid float for trail_length or inputs
            pass

    else:
        # If user hasn't selected "Yes" or "No"
        incline_disabled = True
        decline_disabled = True
        percentagein_disabled = True
        percentagede_disabled = True
        whr_disabled = True

        incline_value = ""
        decline_output = ""
        percentagein_value = ""
        percentagede_value = ""
        inclinedg_value = ""
        declinedg_value = ""
        walkinghr_value = ""

    # ----------------------------------------------------------------------------
    # ----------------------------------------------------------------------------
    if triggered_id == 'update-btn':
        df = load_data_from_gsheet()

        # Just update count & dropdown, do not reset inputs
        return (
            modal_content,
            modal_is_open,
            confirm_reset_displayed,
            trip_count_content,
            confirm_remove_trip_displayed,
            trips_options,
            trip_value,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            incline_disabled,
            decline_disabled,
            percentagein_disabled,
            percentagede_disabled,
            whr_disabled,
            decline_output,
            declinedg_value,
            inclinedg_value,
            percentagein_value,
            percentagede_value,
            walkinghr_value,
            df.to_dict('records')

        )

    # ----------------------------------------------------------------------------
    # 2) reset-btn => user wants to clear entire GSheet except headers
    # ----------------------------------------------------------------------------
    if triggered_id == "reset-btn" and reset_clicks > 0:
        confirm_reset_displayed = True
        return (
            modal_content,
            modal_is_open,
            confirm_reset_displayed,
            trip_count_content,
            confirm_remove_trip_displayed,
            trips_options,
            trip_value,
            dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
            dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
            dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
            dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
            dash.no_update,
            incline_disabled, decline_disabled, percentagein_disabled, percentagede_disabled,
            whr_disabled,
            decline_output, declinedg_value, inclinedg_value, percentagein_value, percentagede_value, walkinghr_value,
            df.to_dict('records')

        )

    # ----------------------------------------------------------------------------
    # 3) confirm_reset => user confirmed clearing GSheet
    # ----------------------------------------------------------------------------
    if triggered_id == "confirm_reset" and confirm_reset > 0:
        clear_gsheet_except_headers()
        modal_content = "DataFrame (Google Sheet) cleared successfully."
        modal_is_open = True

        df_after_clear = load_data_from_gsheet()
        valid_score_count = df_after_clear['Trip'].nunique()
        trip_count_content = f"""
        ### Trips Evaluation Count
        There are **{valid_score_count}** trips.
        """

        # No data => empty dropdown
        trips_options = []
        trip_value = None

        # Reset all fields to defaults
        return (
            modal_content,                 # "modal-body"
            modal_is_open,                 # "score-modal", "is_open"
            confirm_reset_displayed,       # "confirm_reset", "displayed"
            trip_count_content,            # "trips_count"
            confirm_remove_trip_displayed, # "confirm_remove_trip"
            trips_options,                 # "trips_list", "options"
            trip_value,                    # "trips_list", "value"

            defaults["trip"],             # "trip_name"
            defaults["mid_trail_coordinate"],  # "coordinate"
            defaults["trail_link"],
            defaults["area_scores"],
            defaults["Accessibility"],
            defaults["Season"],
            defaults["Challenge"],
            defaults["terrain"],
            defaults["view"],
            defaults["shade"],
            defaults["water"],
            defaults["trail_length"],
            defaults["circular"],
            defaults["required_eq"],
            defaults["weather"],
            defaults["crowdness"],
            defaults["nearby_attractions"],
            defaults["Entry_Fee"],
            defaults["how_far_from_me"],
            defaults["kmh"],

            # Disabling / enabling
            incline_disabled,
            decline_disabled,
            percentagein_disabled,
            percentagede_disabled,
            whr_disabled,

            defaults["decline"],
            defaults["declinedg"],
            defaults["inclinedg"],
            defaults["percentagein"],
            defaults["percentagede"],
            defaults["walkinghr"],
            df_after_removal.to_dict('records')

        )

    # ----------------------------------------------------------------------------
    # 4) remove_btn => user clicked "Remove" for a trip
    # ----------------------------------------------------------------------------
    if triggered_id == "remove_btn" and remove_clicks > 0:
        confirm_remove_trip_displayed = True
        return (
            modal_content,
            modal_is_open,
            confirm_reset_displayed,
            trip_count_content,
            confirm_remove_trip_displayed,
            trips_options,
            trip_value,
            dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
            dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
            dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
            dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
            incline_disabled, decline_disabled, percentagein_disabled, percentagede_disabled,
            whr_disabled,
            decline_output, declinedg_value, inclinedg_value, percentagein_value, percentagede_value, walkinghr_value,
            df.to_dict('records')
        )

    # ----------------------------------------------------------------------------
    # 5) confirm_remove_trip => user confirmed removing the selected trip
    # ----------------------------------------------------------------------------
    if triggered_id == "confirm_remove_trip" and confirm_remove_trip > 0:
        # If no trip is selected
        if trips_list_value is None:
            modal_content = "No Trip Selected"
            modal_is_open = True
            return (
                modal_content,
                modal_is_open,
                confirm_reset_displayed,
                trip_count_content,
                confirm_remove_trip_displayed,
                trips_options,
                trip_value,
                dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
                dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
                dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
                dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
                incline_disabled, decline_disabled, percentagein_disabled, percentagede_disabled,
                whr_disabled,
                decline_output, declinedg_value, inclinedg_value, percentagein_value, percentagede_value, walkinghr_value,
                        df.to_dict('records')

            )

        removed = remove_trip_from_gsheet(trips_list_value)
        if removed:
            modal_content = f"Trip '{trips_list_value}' has been removed."
            df=load_data_from_gsheet()
        else:
            modal_content = f"Trip '{trips_list_value}' not found or could not be removed."
            df=load_data_from_gsheet()

        modal_is_open = True
        # Reload new data
        df_after_removal = load_data_from_gsheet()
        valid_score_count = df_after_removal["Trip"].nunique()
        trip_count_content = f"""
        ### Trips Evaluation Count
        There are **{valid_score_count}** trips.
        """

        # Rebuild dropdown
        if not df_after_removal.empty and "Trip" in df_after_removal.columns:
            new_trips = df_after_removal["Trip"].unique().tolist()
            trips_options = [{'label': t, 'value': t} for t in new_trips]
            trip_value = new_trips[0] if new_trips else None
        else:
            trips_options = []
            trip_value = None

        # Reset fields to defaults
        return (
            modal_content,
            modal_is_open,
            confirm_reset_displayed,
            trip_count_content,
            confirm_remove_trip_displayed,
            trips_options,
            trip_value,

            defaults["trip"],
            defaults["mid_trail_coordinate"],
            defaults["trail_link"],
            defaults["area_scores"],
            defaults["Accessibility"],
            defaults["Season"],
            defaults["Challenge"],
            defaults["terrain"],
            defaults["view"],
            defaults["shade"],
            defaults["water"],
            defaults["trail_length"],
            defaults["circular"],
            defaults["required_eq"],
            defaults["weather"],
            defaults["crowdness"],
            defaults["nearby_attractions"],
            defaults["Entry_Fee"],
            defaults["how_far_from_me"],
            defaults["kmh"],

            incline_disabled,
            decline_disabled,
            percentagein_disabled,
            percentagede_disabled,
            whr_disabled,

            defaults["decline"],
            defaults["declinedg"],
            defaults["inclinedg"],
            defaults["percentagein"],
            defaults["percentagede"],
            defaults["walkinghr"],
        df_after_removal.to_dict('records')

        )

    # ----------------------------------------------------------------------------
    # 6) calculate-btn => main logic to compute a new trip score and append row
    # ----------------------------------------------------------------------------
    if triggered_id == "calculate-btn" and calculate_clicks > 0:
        try:
            # Validate user inputs
            validated_trip_name = trip_name_val(trip_name, df)
            validated_coord = mid_trail_coordinate(coordinate, trail_link, season, df)
            validated_link = link_validity(trail_link, df)

            scr_area = area_scores.get(area, 0)
            scr_access = Accessibility.get(accessibility, 0)
            scr_season = Season.get(season, 0)
            scr_challenge = Challenge.get(challenge, 0)
            scr_terrain = Terrain.get(terrain, 0)
            scr_view = View.get(view, 0)
            scr_shade = Shade.get(shade, 0)
            scr_entry = Entry_Fee.get(entry_fee, 0)
            scr_water = Water.get(water, 0)
            scr_nearby = Nearby_attractions.get(nearby, 0)
            scr_circular = circular.get(circular_val, 0)
            scr_length = trail_length_score(trail_length)
            scr_incline = incline_score(inc) if inc else 0
            scr_incline_pre = inc_precentage_score(incpre) if incpre else 0
            scr_incline_deg = incdeg if incdeg else ""
            scr_decline = decline_score(dec) if dec else 0
            scr_decline_pre = dec_precentage_score(decpre) if decpre else 0
            scr_decline_deg = decdeg if decdeg else ""
            scr_kmh = kmh_validity(kmh)
            scr_walking = walkinghr_scores(walkinghours)
            scr_how_far = How_far_from_me.get(how_far_from_me, 0)
            scr_required_eq = Required_eq.get(required_eq, 0)
            scr_weather = Weather.get(weather, 0)
            scr_crowdness = Crowdness.get(crowdness, 0)

            # Weighted
            weighted_scores (scr_area,scr_access,scr_season,scr_challenge,scr_terrain,scr_view,
               scr_shade,scr_entry,scr_water,scr_nearby,scr_circular,scr_length,scr_incline,scr_decline,scr_incline_pre,
               scr_decline_pre,scr_walking,scr_how_far,scr_required_eq,scr_weather,scr_crowdness)

            total_score = weighted_scores

            # Prepare single row to append
            # NOTE: "scr_incline_deg" and "scr_decline_deg" are not numeric; they’re just strings
            headers = [
                "Trip", "Coordinates", "Trail Link",
                "Area", "Accessibility", "Season", "Challenge", "Terrain", "View", "Shade", "Water", "Circular?",
                "Trail Length", "Incline", "Incline Percentage", "Incline Degree",
                "Decline", "Decline Precentage", "Decline Degree",
                "KM Per Hour", "Walking Hours", "Required EQ", "Weather", "Crowdness",
                "Nearby Attractions", "Entry Fee", "Distance", "Total Score"
            ]

            row_data = [
                validated_trip_name,
                validated_coord,
                validated_link,
                area,
                accessibility,
                season,
                challenge,
                terrain,
                view,
                shade,
                water,
                circular_val,
                trail_length,
                inc,
                incpre,
                scr_incline_deg,
                dec,
                decpre,
                scr_decline_deg,
                scr_kmh,
                walkinghours,
                required_eq,
                weather,
                crowdness,
                nearby,
                entry_fee,
                how_far_from_me,
                total_score
            ]

            # Append row to Google Sheets
            append_row_to_gsheet(row_data, headers)

            # Reload the DF
            df_after_append = load_data_from_gsheet()
            df_filtered = exclude_empty_all_na(df_after_append)

            # Count & update dropdown
            valid_score_count = df_filtered["Trip"].nunique()
            trip_count_content = f"""
            ### Trips Evaluation Count
            There are **{valid_score_count}** trips.
            """

            if not df_filtered.empty and "Trip" in df_filtered.columns:
                new_trips_list = df_filtered["Trip"].unique().tolist()
                trips_options = [{'label': t, 'value': t} for t in new_trips_list]
                trip_value = new_trips_list[0] if new_trips_list else None
            else:
                trips_options = []
                trip_value = None

            # Build success modal
            items = [
                html.Li(f"Trip Name: {validated_trip_name}"),
                html.Li(f"Coordinates: {validated_coord}"),
                html.Li(f"Total Score: {round(total_score,2)}"),
            ]
            modal_content = html.Div([
                html.H2(f"Total Score: {round(total_score,2)}"),
                html.Ul(items),
            ])
            modal_is_open = True

            # Reset all fields to defaults
            return (
                modal_content,        # "modal-body"
                modal_is_open,        # "score-modal", "is_open"
                confirm_reset_displayed,
                trip_count_content,
                confirm_remove_trip_displayed,
                trips_options,        # "trips_list", "options"
                trip_value,           # "trips_list", "value"

                defaults["trip"],                # "trip_name"
                defaults["mid_trail_coordinate"], # "coordinate"
                defaults["trail_link"],
                defaults["area_scores"],
                defaults["Accessibility"],
                defaults["Season"],
                defaults["Challenge"],
                defaults["terrain"],
                defaults["view"],
                defaults["shade"],
                defaults["water"],
                defaults["trail_length"],
                defaults["circular"],
                defaults["required_eq"],
                defaults["weather"],
                defaults["crowdness"],
                defaults["nearby_attractions"],
                defaults["Entry_Fee"],
                defaults["how_far_from_me"],
                defaults["kmh"],

                incline_disabled,
                decline_disabled,
                percentagein_disabled,
                percentagede_disabled,
                whr_disabled,

                defaults["decline"],
                defaults["declinedg"],
                defaults["inclinedg"],
                defaults["percentagein"],
                defaults["percentagede"],
                defaults["walkinghr"],
                df_after_append.to_dict('records')

            )

        except ValueError as e:
            modal_content = html.Div(f"Error: {str(e)}")
            modal_is_open = True
            return (
                modal_content,
                modal_is_open,
                confirm_reset_displayed,
                trip_count_content,
                confirm_remove_trip_displayed,
                trips_options,
                trip_value,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                incline_disabled,
                decline_disabled,
                percentagein_disabled,
                percentagede_disabled,
                whr_disabled,
                decline_output,
                declinedg_value,
                inclinedg_value,
                percentagein_value,
                percentagede_value,
                walkinghr_value,
                df.to_dict('records')

            )

    # ----------------------------------------------------------------------------
    # Default fallback
    # ----------------------------------------------------------------------------
    return (
        modal_content,
        modal_is_open,
        confirm_reset_displayed,
        trip_count_content,
        confirm_remove_trip_displayed,
        trips_options,
        trip_value,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        incline_disabled,
        decline_disabled,
        percentagein_disabled,
        percentagede_disabled,
        whr_disabled,
        decline_output,
        declinedg_value,
        inclinedg_value,
        percentagein_value,
        percentagede_value,
        walkinghr_value,
        df.to_dict('records')
    )




def tab3_layout():
    # Load data from Google Sheets:
    df = df_copy.copy()

    # Check if empty or missing basic columns
    if df.empty or "Trip" not in df.columns:
        return "No DataFrame available from Google Sheets"

    # You previously took columns [3:11] + [21:-1] from the CSV.
    # Adjust this slicing as needed based on your GSheet’s column structure.
    # The below example tries to replicate the same slicing logic if the DataFrame has enough columns.
    col_indices_1 = list(range(3, 11))  # columns 3..10
    col_indices_2 = list(range(21, df.shape[1] - 1))  # columns 21..(last - 1)

    # Collect valid indices that are in range
    valid_col_indices_1 = [i for i in col_indices_1 if i < df.shape[1]]
    valid_col_indices_2 = [i for i in col_indices_2 if i < df.shape[1]]

    # Now build the final list of columns to display in the dropdown
    cols_slice_1 = df.columns[valid_col_indices_1].tolist()
    cols_slice_2 = df.columns[valid_col_indices_2].tolist()
    cols = cols_slice_1 + cols_slice_2

    if not cols:
        return "No valid columns found for filtering."

    default_column = cols[0]  # Default to the first column in that list

    return html.Div(
        style=background_style4,
        children=[
            dcc.Store(id='trip-filter-store'),
            dcc.Store(id='col_sub-store', storage_type='memory'),

            dbc.Container(
                style=container_style,
                children=[
                    html.H1("Trips Filtering", style=heading_style),
                    html.Hr(),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Choose a Filter:"),
                                    dcc.Dropdown(
                                        id='columns',
                                        options=[{'label': k, 'value': k} for k in cols],
                                        placeholder = 'Select a filter',
                                        className="form-control"
                                    )
                                ],
                                width=3
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Choose a Sub Filter:"),
                                    dcc.Dropdown(
                                        id='col_sub',
                                        options=[],  # Initially empty
                                        value="",    # Default value
                                        className="form-control"
                                    ),
                                ],
                                width=3
                            ),
                            
                            dbc.Col(
                                [
                                    dbc.Label("Global Search:"),
                                    dbc.Input(
                                        id='global-search',
                                        placeholder="Search across all columns...",
                                        type='text',
                                        value=''
                                    )
                                ],
                                width=3
                            ),
                        ]
                    ),
                    html.Br(),
                    html.H2("Filters Lists"),
                    html.Br(),
                    dbc.Row([
                        dbc.Col(
                            html.Div([
                                    dash_table.DataTable(
                                        id='selected_filters',
                                        columns=[
                                            {'name': 'Filters', 'id': 'Filters'},
                                            {'name': 'Sub Filters', 'id': 'Sub Filters'}
                                        ],
                                        data=[],     # Will be set dynamically
                                        style_table={
                                            'maxHeight': '200px',
                                            'maxWidth': '800px',
                                            'overflowY': 'auto',
                                            'overflowX': 'auto',
                                            'margin': '10px auto',
                                            'font-size': "20px"
                                        },
                                        style_cell={
                                            'textAlign': 'center',
                                            'padding': '10px',
                                            'minWidth': '150px',
                                            'width': '150px',
                                            'maxWidth': '300px',
                                            'overflow': 'hidden',
                                            'textOverflow': 'ellipsis',
                                        },
                                        style_header={
                                            'backgroundColor': '#f4f4f4',
                                            'fontWeight': 'bold',
                                        },
                                        sort_action='native',
                                        sort_mode='multi',
                                    ),
                    ],
                                    style={
                                        'margin': '0px 0px 0px 0x',
                                        'padding': '20px',
                                        'width': '800px',
                                        'height': '250px',
                                        'border': '1px solid',
                                        'borderRadius': '5px',
                                    }
                                )                                
                            ),
                        dbc.Col(
                        dbc.Button(
                                    "Filter",
                                    id='filter_btn',
                                    color='success',
                                    n_clicks=0,
                                    style=button_style_filter
                                ),
                        width=2)
                    ]
                ),
                    dbc.Row([
                        dbc.Col(
                            [
                                html.Div([
                                    dash_table.DataTable(
                                        id='selected_trips',
                                        columns=[],  # Will be set dynamically
                                        data=[],     # Will be set dynamically
                                        row_selectable='single',
                                        style_table={
                                            'maxHeight': '400px',
                                            'maxWidth': '1300px',
                                            'overflowY': 'auto',
                                            'overflowX': 'auto',
                                            'margin': '10px auto',
                                            'font-size': "20px"
                                        },
                                        style_cell={
                                            'textAlign': 'center',
                                            'padding': '10px',
                                            'minWidth': '150px',
                                            'width': '150px',
                                            'maxWidth': '300px',
                                            'overflow': 'hidden',
                                            'textOverflow': 'ellipsis',
                                        },
                                        style_header={
                                            'backgroundColor': '#f4f4f4',
                                            'fontWeight': 'bold',
                                        },
                                        sort_action='native',
                                        sort_mode='multi',
                                    ),
                            ],
                                    style={
                                        'margin': '0px 0px 0px 0x',
                                        'padding': '20px',
                                        'width': '1300px',
                                        'height': '450px',
                                        'border': '1px solid #444',
                                        'borderRadius': '5px',
                                    }, 
                                ),
                                html.Br(),
                                dbc.Button(
                                    "Reset All Filters",
                                    id='reset_filters',
                                    color='success',
                                    n_clicks=0,
                                    style=button_style7
                                ),
                                dbc.Button(
                                    "Add To Comparison",
                                    id='comp_trip',
                                    color='success',
                                    n_clicks=0,
                                    style=button_style9
                                ),

                                html.H2("Trips Comparison"),
                                html.Div(
                                    dash_table.DataTable(
                                        id='multi_trips_selection',
                                        columns=[],  # Dynamically added
                                        data=[],     # Dynamically added
                                        style_table={
                                            'maxHeight': '400px',
                                            'maxWidth': '2450px',
                                            'overflowY': 'auto',
                                            'overflowX': 'auto',
                                            'margin': '10px auto',
                                            'font-size': "20px"
                                        },
                                        style_cell={
                                            'textAlign': 'center',
                                            'padding': '10px',
                                            'minWidth': '150px',
                                            'width': '150px',
                                            'maxWidth': '300px',
                                            'overflow': 'visible',
                                            'whiteSpace': 'normal'
                                        },
                                        style_header={
                                            'backgroundColor': '#f4f4f4',
                                            'fontWeight': 'bold',
                                        },
                                        sort_action='native',
                                        sort_mode='multi',
                                    ),
                                    style={
                                        'margin': '0px 0px 0px 0x',
                                        'padding': '20px',
                                        'width': '2450px',
                                        'height': '450px',
                                        'border': '1px solid #444',
                                        'borderRadius': '5px',
                                    }
                                ),
                                html.Br(),
                                dbc.Button(
                                    "Clear Table",
                                    id='reset_table',
                                    color='success',
                                    n_clicks=0,
                                    style=button_style8
                                ),

                            ],
                            width=8
                        ),

                        dbc.Col(
                            html.Iframe(
                                id='picked_trek_map',
                                src="",
                                style={
                                    "width": "1150px",
                                    "height": "550px",
                                    "width-max": "300px",
                                    "border": "2px solid black",
                                    "margin": "0px 0px 0px -350px",
                                },
                            ),
                            width=4
                        )
                    ]),
                ]
            )
        ]
    )


@app.callback(
    [
        Output('col_sub', 'options'),
        Output('col_sub', 'value'),
        Output('columns', 'value'),
    ],
    [
        Input('columns', 'value'),
        Input('reset_filters', 'n_clicks'),

    ]
)
def update_sub_filter_options(selected_column, reset_clicks):

    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    # Load from GSheets
    df = load_data_from_gsheet()

    if df.empty or selected_column not in df.columns or selected_column is None:
        return [], "",""

    # Build sub-options for the chosen column
    unique_vals = df[selected_column].dropna().unique().tolist()
    sub_options = [{'label': str(v), 'value': v} for v in unique_vals]
    

    # If triggered by reset_filters => reset to 'Area' (example) or any logic you choose
    if triggered_id == 'reset_filters':
        return [], "", ""

    # Otherwise triggered by 'columns' => user picked a new column
    return sub_options, "", selected_column


@app.callback(
    [
        Output('selected_trips', 'columns'),
        Output('selected_trips', 'data'),
        Output('picked_trek_map', 'src'),
        Output('multi_trips_selection', 'columns'),
        Output('multi_trips_selection', 'data'),
        Output("selected_filters", "data")
    ],
    [
        Input('columns', 'value'),
        Input('col_sub', 'value'),
        Input('global-search', 'value'),
        Input ("selected_filters", "data"),
        Input ("filter_btn",'n_clicks'),
        Input('selected_trips', 'selected_rows'),
        Input('comp_trip', 'n_clicks'),
        Input('reset_table', 'n_clicks'),
        
    ],
    [
        State('multi_trips_selection', 'data'),
        State("selected_filters", "data"),
    ]
)
def display_filtered_trips(columns, col_sub, global_search,
                           selected_filters,filter_btn,selected_rows, compare_clicks, reset_clicks,
                           multi_trips_data, selected_filters_state):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
    if not isinstance(multi_trips_data, list):
        multi_trips_data = []

    multi_trips_columns = dash.no_update
    # Load from Google Sheets
    df4 = df_copy.copy()
    if df4.empty:
        return [], [], "", [], [], []

    if columns not in df4.columns or "Trip" not in df4.columns:
        return [], [], "", [], [], []

    # Global search across all columns
    if global_search:
        df4 = df4[
            df4.apply(
                lambda row: row.astype(str).str.contains(global_search, case=False).any(),
                axis=1
            )
        ]

    # Column-based filter
    if col_sub:
        if col_sub in df4[columns].unique():
            df4 = df4[df4[columns] == col_sub]

            # Initialize selected_filters_state if it's None
            if selected_filters_state is None:
                selected_filters_state = []

            # Check if columns already exists in selected_filters_state
            existing_filter = next((filter_item for filter_item in selected_filters_state if filter_item['Filters'] == columns), None)

            if existing_filter:
                # If the column exists but the sub filter is different, update the sub filter
                if existing_filter['Sub Filters'] != col_sub:
                    existing_filter['Sub Filters'] = col_sub
            else:
                # Append the new filter if it doesn't exist
                new_filter = {'Filters': columns, 'Sub Filters': col_sub}
                selected_filters_state.append(new_filter)

    elif col_sub == '' and columns == '':
        selected_filters_state = []



    # Sort by "Total Score" if it exists
    if "Total Score" in df4.columns:
        df4["Total Score"] = pd.to_numeric(df4["Total Score"], errors='coerce').fillna(0)
        df4 = df4.sort_values(by="Total Score", ascending=False)
        
    selected_trip_link = ""    
    if triggered_id == 'filter_btn':
    # Build the columns for 'selected_trips' table
        selected_trips_columns = [
            {'name': 'Trip', 'id': 'Trip'},
            {'name': 'Total Score', 'id': 'Total Score'},
            {'name': 'Trail Link', 'id': 'Trail Link'},
        ]

        # Dynamically add filter columns based on selected filters
        if selected_filters_state:
            for filter_entry in selected_filters_state:
                filter_name = filter_entry.get('Filters')
                if filter_name:
                    column_name = f"Filter: {filter_name}"
                    selected_trips_columns.append({'name': column_name, 'id': column_name})

        # Apply all selected filters to the DataFrame
        for filter_entry in selected_filters_state or []:
            filter_column = filter_entry.get('Filters')
            sub_filter = filter_entry.get('Sub Filters')
            if filter_column in df4.columns and sub_filter:
                df4 = df4[df4[filter_column] == sub_filter]
        
        global df4_subset
        df4_subset = df4[['Trip', 'Total Score', 'Trail Link']].copy()

        # Add each filter and its corresponding sub-filter to the data
        for filter_entry in selected_filters_state or []:
            filter_name = filter_entry.get('Filters')
            sub_filter = filter_entry.get('Sub Filters')
            if filter_name:
                column_name = f"Filter: {filter_name}"
                df4_subset[column_name] = sub_filter

        # Convert the DataFrame to a list of dictionaries
        selected_trips_data = df4_subset.to_dict('records')

        return (
            selected_trips_columns,
            selected_trips_data,
            selected_trip_link,
            multi_trips_columns,
            multi_trips_data or [],
            selected_filters_state
        )

    elif triggered_id == 'reset_table' and reset_clicks > 0:
        multi_trips_data = []
        
    # Preserve multi_trips_data even when a row is selected
        selected_trip_link = ""
    elif selected_rows and len(selected_rows) > 0:
        row_idx = selected_rows[0]
        if row_idx < len(df4_subset):
            selected_trip_link = df4_subset.iloc[row_idx]["Trail Link"]

            if triggered_id == 'comp_trip' and compare_clicks > 0:
                comp_cols = [
                    'Trip', 'Area', 'Entry Fee', 'Challenge', 'View', 'Shade',
                    'Water', 'Walking Hours', "Circular?", "Required Equipment",
                    'Distance', 'Total Score'
                ]
                comp_cols = [c for c in comp_cols if c in df4.columns]
                row_comp_data = df4.loc[df4_subset.index[row_idx], comp_cols]
                row_comp_dict = row_comp_data.to_dict()

                # Ensure multi_trips_data is a list
                if not isinstance(multi_trips_data, list):
                    multi_trips_data = []

                # Append the selected trip if not already in the list
                if row_comp_dict not in multi_trips_data:
                    multi_trips_data.append(row_comp_dict)

            comp_cols = [
                'Trip', 'Area', 'Entry Fee', 'Challenge', 'View', 'Shade',
                'Water', 'Walking Hours', "Circular?", "Required Equipment",
                'Distance', 'Total Score'
            ]
            comp_cols = [c for c in comp_cols if c in df4.columns]
            multi_trips_columns = [{'name': c, 'id': c} for c in comp_cols]

            return (
                dash.no_update,
                dash.no_update,
                selected_trip_link,
                multi_trips_columns,
                multi_trips_data,
                selected_filters_state
            )




    return [], [], "", [], [], selected_filters_state



def create_histogram(df):
    # Basic check to ensure 'Trail Length' column exists and is numeric
    if 'Trail Length' not in df.columns:
        # Return an empty figure or raise an exception
        return go.Figure()

    # Ensure numeric
    df['Trail Length'] = pd.to_numeric(df['Trail Length'], errors='coerce')
    df.dropna(subset=['Trail Length'], inplace=True)

    # Calculate histogram data
    hist_data = np.histogram(df['Trail Length'], bins=5)
    bin_edges = hist_data[1]
    bin_counts = hist_data[0]

    colors = px.colors.qualitative.Prism_r
    fig = go.Figure()

    # Add bars
    for i in range(len(bin_counts)):
        fig.add_trace(go.Bar(
            x=[(bin_edges[i] + bin_edges[i + 1]) / 2],
            y=[bin_counts[i]],
            width=[bin_edges[i + 1] - bin_edges[i]],
            marker_color=colors[i % len(colors)],
            text=[bin_counts[i]],
            textposition='outside',
            name=f'Bin {i + 1}',
            hovertext=f'Bin {i + 1}: {bin_counts[i]}',
            hoverinfo='text'
        ))

    # Overlay line over bins
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    fig.add_trace(go.Scatter(
        x=bin_centers,
        y=bin_counts,
        mode='lines+markers',
        line=dict(color='black', width=2),
        name='Frequency Line'
    ))

    fig.update_layout(
        title=dict(text='Histogram of Trail Length', font=dict(size=32)),
        xaxis=dict(
            title=dict(text='Trail Length (in KM)', font=dict(size=22)),
            tickfont=dict(size=22)
        ),
        yaxis=dict(
            title=dict(text='Count', font=dict(size=22)),
            tickfont=dict(size=22),
            range=[0, bin_counts.max() + 2]
        ),
        barmode='overlay',
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font=dict(size=22))
    )
    
    fig.update_traces(
        textfont=dict(size=24)
    )

    return fig


def create_scatter_plot(df):
    """
    Expects that 'Walking Hours (hours)' and 'Total Score' columns exist.
    If not, returns an empty figure or simply ignores them.
    """
    if 'Walking Hours (hours)' not in df.columns or 'Total Score' not in df.columns:
        return go.Figure()

    # Convert to numeric
    df['Walking Hours (hours)'] = pd.to_numeric(df['Walking Hours (hours)'], errors='coerce')
    df['Total Score'] = pd.to_numeric(df['Total Score'], errors='coerce')
    df.dropna(subset=['Walking Hours (hours)', 'Total Score'], inplace=True)

    # Sort by walking hours
    sorted_data = df.sort_values(by='Walking Hours (hours)')
    x_values = sorted_data['Walking Hours (hours)']
    y_values = sorted_data['Total Score']

    fig = px.scatter(
        df,
        x='Walking Hours (hours)',
        y='Total Score',
        title='Total Score vs Walking Hours (Hours)',
        labels={'Walking Hours (hours)': 'Walking Hours (Hours)', 'Total Score': 'Total Score'},
        color_discrete_sequence=['orange']
    )
    fig.update_traces(
        marker=dict(size=12),
        textfont=dict(size=28),
        hoverlabel=dict(font=dict(size=22))
    )

    # Add regression-like connecting line
    fig.add_scatter(
        x=x_values,
        y=y_values,
        mode='lines',
        name='Connecting Line',
        line=dict(color='blue', dash='solid')
    )

    fig.update_layout(
        title=dict(font=dict(size=32)),
        xaxis_title='Walking Hours (Hours)',
        yaxis_title='Total Score',
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(size=22),
        xaxis=dict(title=dict(font=dict(size=22)), tickfont=dict(size=22)),
        yaxis=dict(title=dict(font=dict(size=22)), tickfont=dict(size=22)),
        hoverlabel=dict(font=dict(size=22))
    )
    return fig


def tab4_layout():
    df5 = load_data_from_gsheet()

    if df5.empty or 'Trip' not in df5.columns:
        return "No data available from Google Sheets"

    # Convert columns if they exist
    if 'Walking Hours' in df5.columns:
        df5['Walking Hours (hours)'] = df5['Walking Hours'].str.split(':').apply(
            lambda x: round(int(x[0]) + int(x[1]) / 60, 2) if isinstance(x, list) and len(x) == 2 else None
        )

    # Example conversions to numeric
    if 'Total Score' in df5.columns:
        df5['Total Score'] = pd.to_numeric(df5['Total Score'], errors='coerce')

    # Create the “top 10 by total score” bar chart:
    df_sorted = df5.sort_values(by='Total Score', ascending=False).head(10)
    bar_chart1 = px.bar(
        df_sorted,
        x='Trip',
        y='Total Score',
        color='Total Score',
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    bar_chart1.update_traces(
        text=round(df_sorted['Total Score'], 3),
        textposition='outside',
        textfont=dict(size=22)
    )
    bar_chart1.update_layout(
        font=dict(size=24),
        yaxis=dict(
            range=[0, df_sorted['Total Score'].max() + 2],
            title=dict(text="Total Score", font=dict(size=22)),
            tickfont=dict(size=18),
            tick0=0,
            dtick=round(df_sorted['Total Score'].max() / 10) if not df_sorted.empty else 1
        ),
        xaxis=dict(
            title=dict(text="Trip", font=dict(size=22)),
            tickfont=dict(size=18)
        ),
        title=dict(text="Top 10 Trips by Total Score", font=dict(size=32)),
        coloraxis_showscale=False,
        showlegend=False,
        width=1200,
        height=800,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font=dict(size=20))
    )

    # Example grouping by Season
    if 'Season' in df5.columns:
        df_grouped = df5.groupby('Season')['Trip'].count().reset_index()
        df_grouped.columns = ['Season', 'Count']
        pie_chart1 = px.pie(
            df_grouped,
            names='Season',
            values='Count',
            title='Trips by Travelled Season',
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        pie_chart1.update_layout(
            font=dict(size=18),
            title=dict(font=dict(size=32)),
            width=720,
            height=800,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            hoverlabel=dict(font=dict(size=20))
        )
        pie_chart1.update_traces(textfont=dict(size=24))
    else:
        # Fallback if Season isn't in your sheet
        pie_chart1 = go.Figure()

    # Example area breakdown
    if 'Area' in df5.columns:
        area_df = df5['Area'].value_counts().reset_index()
        area_df.columns = ['Area', 'Count']
        pie_chart2 = px.pie(
            area_df,
            names='Area',
            values='Count',
            title='Trips by Area',
            color_discrete_sequence=px.colors.qualitative.Prism_r
        )
        pie_chart2.update_layout(
            font=dict(size=18),
            title=dict(font=dict(size=32)),
            width=870,
            height=800,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            hoverlabel=dict(font=dict(size=20))
        )
        pie_chart2.update_traces(textfont=dict(size=24))
    else:
        pie_chart2 = go.Figure()

    # Top 10 by trail length
    if 'Trail Length' in df5.columns:
        # Ensure Trail Length is numeric
        df5['Trail Length'] = pd.to_numeric(df5['Trail Length'], errors='coerce').fillna(0)
        
        # Sort and get top 10 by Trail Length
        df_length = df5.sort_values(by='Trail Length', ascending=False).head(10)
        
        # Create the bar chart
        bar_chart2 = px.bar(
            df_length,
            x='Trip',
            y='Trail Length',
            color='Trail Length',
            color_continuous_scale=px.colors.sequential.Electric
        )
        bar_chart2.update_traces(
            text=round(df_length['Trail Length'], 3),
            textposition='outside',
            textfont=dict(size=22)
        )
        bar_chart2.update_layout(
            font=dict(size=24),
            yaxis=dict(
                range=[0, df_length['Trail Length'].max() + 3],
                title=dict(text="Trail Length", font=dict(size=22)),
                tickfont=dict(size=18),
                tick0=0,
                dtick=round(df_length['Trail Length'].max() / 10) if not df_length.empty else 1
            ),
            xaxis=dict(
                title=dict(text="Trip", font=dict(size=22)),
                tickfont=dict(size=18)
            ),
            title=dict(text="Top 10 Trips by Trail Length", font=dict(size=32)),
            coloraxis_showscale=False,
            showlegend=False,
            width=1200,
            height=800,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            hoverlabel=dict(font=dict(size=20))
        )
    else:
        bar_chart2 = go.Figure()



    # Example annotation
    if not df5.empty and 'Trail Length' in df5.columns:
        var_length = df5['Trail Length'].head(10).var()  # or some other slice
        bar_chart2.add_annotation(
            xref="paper",
            yref="paper",
            x=1.0,
            y=0.90,
            text=f"Length Variance: {var_length:.2f}",
            showarrow=False,
            font=dict(size=18, color='white', weight='bold'),
            align="right",
            bgcolor='black',
            bordercolor='white',
            borderwidth=2,
            borderpad=4
        )

    # Steep Value logic
    if 'Incline' in df5.columns and 'Decline' in df5.columns:
        df5['Incline'] = pd.to_numeric(df5['Incline'], errors='coerce').fillna(0)
        df5['Decline'] = pd.to_numeric(df5['Decline'], errors='coerce').fillna(0)
        df5['Steep Value'] = df5[['Incline', 'Decline']].max(axis=1)
        top_5_steep = df5.nlargest(5, 'Steep Value')
        bar_chart_3 = px.bar(
            top_5_steep,
            x='Trip',
            y='Steep Value',
            title="Top 5 Trails with the Steepest Incline or Decline",
            labels={'Trip': 'Trail Name', 'Steep Value': 'Steepness (In Meters)'},
            color='Steep Value',
            color_continuous_scale=px.colors.qualitative.G10_r,
            text='Steep Value'
        )
        bar_chart_3.update_layout(
            title=dict(font=dict(size=32)),
            xaxis=dict(title=dict(font=dict(size=22)), tickfont=dict(size=22)),
            yaxis=dict(title=dict(font=dict(size=22)), tickfont=dict(size=22),
                       range=[0, df5['Incline'].max() + 500]),
            coloraxis_showscale=False,
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )
        bar_chart_3.update_traces(
            hoverlabel=dict(font=dict(size=22)),
            textposition='outside',
            textfont=dict(size=22)
        )
    else:
        bar_chart_3 = go.Figure()

    # Generate histogram & scatter
    histogram_plot = create_histogram(df5)
    scatter_plot = create_scatter_plot(df5)

    # Build the layout with a dash Container + Graph elements
    return html.Div(
        style=background_style4,
        children=[
            dcc.Interval(id='interval-dashboard', interval=1 * 10000, n_intervals=0),
            dcc.Store(id='trip-dashboard-store'),
            dbc.Container(
                style=container_style,
                children=[
                    html.H1("Trips Dashboard", style=heading_style),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col(dcc.Graph(id='area_pie', figure=pie_chart2)),
                        dbc.Col(dcc.Graph(id='length_hist', figure=histogram_plot)),
                        dbc.Col(dcc.Graph(id='season_pie', figure=pie_chart1)),
                    ]),
                    dbc.Row([
                        dbc.Col(dcc.Graph(id='length_chart', figure=bar_chart2)),
                        dbc.Col(dcc.Graph(id='trips_chart', figure=bar_chart1)),
                    ]),
                    dbc.Row([
                        dbc.Col(dcc.Graph(id='scatter_plot', figure=scatter_plot)),
                        dbc.Col(dcc.Graph(id='steep_bar', figure=bar_chart_3)),
                    ])
                ]
            )
        ]
    )


@app.callback(
    [
        Output('trips_chart', 'figure'),
        Output('season_pie', 'figure'),
        Output('area_pie', 'figure'),
        Output('length_chart', 'figure'),
        Output('length_hist', 'figure'),
        Output('scatter_plot', 'figure'),
        Output('steep_bar', 'figure'),
    ],
    [Input('interval-dashboard', 'n_intervals')]
)
def update_figures(n_intervals):
    """
    Periodically refresh data from Google Sheets and recalculate all figures.
    If the sheet is empty or missing columns, we do PreventUpdate.
    """
    df_c = df_global
    if df_c.empty or 'Trip' not in df_c.columns:
        raise dash.exceptions.PreventUpdate

    # Convert columns as needed
    if 'Walking Hours' in df_c.columns:
        df_c['Walking Hours (hours)'] = df_c['Walking Hours'].str.split(':').apply(
            lambda x: round(int(x[0]) + int(x[1]) / 60, 2) if isinstance(x, list) and len(x) == 2 else None
        )
    if 'Total Score' in df_c.columns:
        df_c['Total Score'] = pd.to_numeric(df_c['Total Score'], errors='coerce')
        
    if 'Trail Length' in df_c.columns:
        df_c['Trail Length'] = pd.to_numeric(df_c['Trail Length'], errors='coerce').fillna(0)

    # 1) bar_chart1 => top 10 by total score
    if 'Total Score' in df_c.columns:
        df_sorted = df_c.sort_values(by='Total Score', ascending=False).head(10)
    else:
        df_sorted = df_c.copy()

    bar_chart1 = px.bar(
        df_sorted,
        x='Trip',
        y='Total Score',
        color='Total Score',
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    bar_chart1.update_traces(
        text=round(df_sorted['Total Score'].fillna(0), 3),
        textposition='outside',
        textfont=dict(size=22)
    )
    bar_chart1.update_layout(
        font=dict(size=24),
        yaxis=dict(
            range=[0, df_sorted['Total Score'].max() + 2] if not df_sorted.empty else [0, 10],
            title=dict(text="Total Score", font=dict(size=22)),
            tickfont=dict(size=18),
            tick0=0,
            dtick=round(df_sorted['Total Score'].max() / 10) if not df_sorted.empty else 1
        ),
        xaxis=dict(
            title=dict(text="Trip", font=dict(size=22)),
            tickfont=dict(size=18)
        ),
        title=dict(text="Top 10 Trips by Total Score", font=dict(size=32)),
        coloraxis_showscale=False,
        showlegend=False,
        width=1200,
        height=800,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font=dict(size=20))
    )

    # 2) season_pie => "Season" grouping
    if 'Season' in df_c.columns:
        df_grouped = df_c.groupby('Season')['Trip'].count().reset_index()
        df_grouped.columns = ['Season', 'Count']
        pie_chart1 = px.pie(
            df_grouped,
            names='Season',
            values='Count',
            title='Trips by Travelled Season',
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        pie_chart1.update_layout(
            font=dict(size=18),
            title=dict(font=dict(size=32)),
            width=720,
            height=800,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            hoverlabel=dict(font=dict(size=20))
        )
        pie_chart1.update_traces(textfont=dict(size=24))
    else:
        pie_chart1 = go.Figure()

    # 3) area_pie => "Area" breakdown
    if 'Area' in df_c.columns:
        area_df = df_c['Area'].value_counts().reset_index()
        area_df.columns = ['Area', 'Count']
        pie_chart2 = px.pie(
            area_df,
            names='Area',
            values='Count',
            title='Trips by Area',
            color_discrete_sequence=px.colors.qualitative.Prism_r
        )
        pie_chart2.update_layout(
            font=dict(size=18),
            title=dict(font=dict(size=32)),
            width=870,
            height=800,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            hoverlabel=dict(font=dict(size=20))
        )
        pie_chart2.update_traces(textfont=dict(size=24))
    else:
        pie_chart2 = go.Figure()

    # 4) length_chart => top 10 by "Trail Length"
    if 'Trail Length' in df_c.columns:
        df_length = df_c.sort_values(by='Trail Length', ascending=False).head(10)
        bar_chart2 = px.bar(
            df_length,
            x='Trip',
            y='Trail Length',
            color='Trail Length',
            color_continuous_scale=px.colors.sequential.Electric
        )
        bar_chart2.update_traces(
            text=round(df_length['Trail Length'].fillna(0), 3),
            textposition='outside',
            textfont=dict(size=22)
        )
        bar_chart2.update_layout(
            font=dict(size=24),
            yaxis=dict(
                range=[0, df_length['Trail Length'].max() + 3] if not df_length.empty else [0, 10],
                title=dict(text="Trail Length", font=dict(size=22)),
                tickfont=dict(size=18),
                tick0=0,
                dtick=1
            ),
            xaxis=dict(
                title=dict(text="Trip", font=dict(size=22)),
                tickfont=dict(size=18)
            ),
            title=dict(text="Top 10 Trips by Trail Length", font=dict(size=32)),
            coloraxis_showscale=False,
            showlegend=False,
            width=1200,
            height=800,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            hoverlabel=dict(font=dict(size=20))
        )
    else:
        bar_chart2 = go.Figure()

    # 5) length_hist => histogram
    histogram_plot = create_histogram(df_c)

    # 6) scatter_plot => scatter
    scatter_plot = create_scatter_plot(df_c)

    # 7) steep_bar => top 5 by "Steep Value"
    if 'Incline' in df_c.columns and 'Decline' in df_c.columns:
        df_c['Incline'] = pd.to_numeric(df_c['Incline'], errors='coerce').fillna(0)
        df_c['Decline'] = pd.to_numeric(df_c['Decline'], errors='coerce').fillna(0)
        df_c['Steep Value'] = df_c[['Incline', 'Decline']].max(axis=1)
        top_5_steep = df_c.nlargest(5, 'Steep Value')
        bar_chart_3 = px.bar(
            top_5_steep,
            x='Trip',
            y='Steep Value',
            title="Top 5 Trails with the Steepest Incline or Decline",
            labels={'Trip': 'Trail Name', 'Steep Value': 'Steepness (In Meters)'},
            color='Steep Value',
            color_continuous_scale=px.colors.qualitative.G10_r,
            text='Steep Value'
        )
        bar_chart_3.update_layout(
            title=dict(font=dict(size=32)),
            xaxis=dict(title=dict(font=dict(size=22)), tickfont=dict(size=22)),
            yaxis=dict(title=dict(font=dict(size=22)), tickfont=dict(size=22),
                       range=[0, df_c['Incline'].max() + 500]),
            coloraxis_showscale=False,
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )
        bar_chart_3.update_traces(
            hoverlabel=dict(font=dict(size=22)),
            textposition='outside',
            textfont=dict(size=22)
        )
    else:
        bar_chart_3 = go.Figure()

    return (
        bar_chart1,     # trips_chart
        pie_chart1,     # season_pie
        pie_chart2,     # area_pie
        bar_chart2,     # length_chart
        histogram_plot, # length_hist
        scatter_plot,   # scatter_plot
        bar_chart_3     # steep_bar
    )
    
    
def tab5_layout():
    df6=df_global.copy()
    trip_options_edit = df6["Trip"].unique().tolist() if not df6.empty else []
    trip_count_edit = df6["Trip"].nunique() if not df6.empty else 0
    return html.Div(
    style=background_style,
    children=[
        dcc.Store(id='df_edit_store'),
        dcc.Store(id='trip_name_store_edit'),  # <-- New Store Added Here
        dcc.Store(id="load_clicks_store"),
        dbc.Container(
            style=container_style,
            children=[
                html.H1("Trip Editor", style=heading_style),
                html.Hr(),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H5("Name & Location"),
                                dbc.Label("Trip Name:"),
                                dcc.Input(id='trip_name_edit', type='text', value="", className="form-control",disabled=True),
                                html.Br(),
                                dbc.Label("Accessibility:"),
                                dcc.Dropdown(
                                    id='accessibility_edit',
                                    options=[{'label': k, 'value': k} for k in Accessibility.keys()],
                                    value="",
                                    className="form-control"
                                ),
                                html.Br(),
                                dbc.Label("Travelled Season:"),
                                dcc.Dropdown(
                                    id='Season_edit',
                                    options=[{'label': k, 'value': k} for k in Season.keys()],
                                    value="",
                                    className="form-control"
                                ),
                                html.Br(),
                                dbc.Label("Trail Length:"),
                                dcc.Input(id='trail_length_edit', type='text', value="", className="form-control",disabled=True),
                                html.Br(),
                                dbc.Label("Is It Circular?"),
                                html.Br(),
                                dcc.Dropdown(
                                    id='circular_edit',
                                    options=[{'label': k, 'value': k} for k in circular.keys()],
                                    value="",
                                    className="form-control",
                                    disabled=True
                                ),
                                html.Br(),
                                dbc.Label("Estimated Travel Time:"),
                                html.Br(),
                                dcc.Input(
                                    id='kmh_edit', type='text', value="",
                                    className="form-control",
                                    style={"display": "inline-block", "width": "45%"}
                                ),
                                dbc.Label("KM/H", style={"margin-left": "10px"}),
                                html.Br(),
                                dcc.Input(
                                    id='walkinghr_edit', type='text', value="",
                                    className="form-control",
                                    style={"display": "inline-block", "width": "45%"},
                                    disabled=True
                                ),
                                dbc.Label("Hours", style={"margin-left": "10px", "margin-right": "10px"}),
                                html.Br(),
                                html.Br(),
                                dbc.Button("Update DB", id='update-btn_edit', color='primary', n_clicks=0, style=button_style_11_tab5),
                                html.Br(),
                                dcc.Markdown(
                                    id='trips_count_edit',
                                    children=f"### Trips Evaluation Count\nThere are **{trip_count_edit}** trips.",
                                    style={'fontSize': '24px', 'marginTop': '20px'}
                                ),
                                dcc.Dropdown(
                                    id='trips_list_edit',
                                    options=[{'label': t, 'value': t} for t in trip_options_edit],
                                    value=trip_options_edit[0] if trip_options_edit else None,
                                    className="form-control"
                                ),
                                dbc.Button("Remove", id='remove_btn_edit', color='success', n_clicks=0, style=button_style3_tab5),
                                dcc.ConfirmDialog(
                                    id='confirm_remove_trip_edit',
                                    message="Are you sure you want to remove this trip? This action cannot be undone.",
                                ),
                                dbc.Button("Load Trip", id='load_btn_edit', color='success', n_clicks=0, style=button_style13),
                            ],
                            width=2
                        ),
                        dbc.Col(
                            [
                                html.H5("Trail Features"),
                                dbc.Label("Challenge:"),
                                dcc.Dropdown(
                                    id='challenge_edit',
                                    options=[{'label': c, 'value': c} for c in Challenge.keys()],
                                    value="",
                                    className="form-control"
                                ),
                                html.Br(),
                                dbc.Label("Terrain:"),
                                dcc.Dropdown(
                                    id='terrain_edit',
                                    options=[{'label': k, 'value': k} for k in Terrain.keys()],
                                    value="",
                                    className="form-control"
                                ),
                                html.Br(),
                                dbc.Label("View:"),
                                dcc.Dropdown(
                                    id='view_edit',
                                    options=[{'label': k, 'value': k} for k in View.keys()],
                                    value="",
                                    className="form-control"
                                ),
                                html.Br(),
                                dbc.Label("How Shaded?"),
                                dcc.Dropdown(
                                    id='shade_edit',
                                    options=[{'label': k, 'value': k} for k in Shade.keys()],
                                    value="",
                                    className="form-control"
                                ),
                                html.Br(),
                                dbc.Label("Water:"),
                                dcc.Dropdown(
                                    id='water_edit',
                                    options=[{'label': k, 'value': k} for k in Water.keys()],
                                    value="",
                                    className="form-control"
                                ),
                                html.Br(),
                                dbc.Label("Required Equipment:"),
                                dcc.Dropdown(
                                    id='required_eq_edit',
                                    options=[{'label': k, 'value': k} for k in Required_eq.keys()],
                                    value="",
                                    className="form-control"
                                ),
                            ],
                            width=3
                        ),
                        dbc.Col(
                            [
                                html.H5("General Conditions"),
                                dbc.Label("Weather:"),
                                dcc.Dropdown(
                                    id='weather_edit',
                                    options=[{'label': k, 'value': k} for k in Weather.keys()],
                                    value="",
                                    className="form-control"
                                ),
                                html.Br(),
                                dbc.Label("Crowdness:"),
                                dcc.Dropdown(
                                    id='crowdness_edit',
                                    options=[{'label': k, 'value': k} for k in Crowdness.keys()],
                                    value="",
                                    className="form-control"
                                ),
                                html.Br(),
                                dbc.Label("Nearby Attractions:"),
                                dcc.Dropdown(
                                    id='nearby_edit',
                                    options=[{'label': k, 'value': k} for k in Nearby_attractions.keys()],
                                    value="",
                                    className="form-control"
                                ),
                                html.Br(),
                                dbc.Label("Entry Fee:"),
                                dcc.Dropdown(
                                    id='Entry_Fee_edit',
                                    options=[{'label': k, 'value': k} for k in Entry_Fee.keys()],
                                    value="",
                                    className="form-control"
                                ),
                                html.Br(),
                                dbc.Label("How Far Is It?"),
                                dcc.Dropdown(
                                    id='how_far_from_me_edit',
                                    options=[{'label': k, 'value': k} for k in How_far_from_me.keys()],
                                    value="",
                                    className="form-control"
                                ),
                                html.Br(),
                                dbc.Button("Save Updates", id='apply-btn', color='primary', n_clicks=0, style=button_style_tab5),
                                dcc.ConfirmDialog(
                                    id='confirm_apply_trip_edit',
                                    message="Are you sure you want to save updates?",
                                ),
                                dbc.Button("Remove DataFrame", id='reset-btn_edit', color='primary', n_clicks=0, style=button_style_tab5_2),
                                dcc.ConfirmDialog(
                                    id='confirm_reset_edit',
                                    message="Are you sure you want to clear the DataFrame? This action cannot be undone.",
                                ),
                                dbc.Modal(
                                    [
                                        dbc.ModalHeader("Trip Score"),
                                        dbc.ModalBody(id="modal-body_edit"),
                                    ],
                                    id="edit-modal_edit",
                                    is_open=False,
                                ),
                            ],
                            width=3
                        )
                    ]
                ),
            ]
        )
    ]
)


@app.callback(
    [
        Output("modal-body_edit", "children"),
        Output("edit-modal_edit","is_open"),
        Output("trips_list_edit", "options"),
        Output("trips_list_edit", "value"),
        Output("trips_count_edit", "children"),
        Output("confirm_remove_trip_edit", "displayed"),
        Output("confirm_reset_edit", "displayed"),
        Output("confirm_apply_trip_edit", "displayed"),
        Output("trip_name_edit", "value"),
        Output("accessibility_edit", "value"),
        Output("Season_edit", "value"),
        Output("trail_length_edit","value"),
        Output("circular_edit", "value"),
        Output("kmh_edit", "value"),
        Output("walkinghr_edit", "value"),
        Output("challenge_edit", "value"),
        Output("terrain_edit", "value"),
        Output("view_edit", "value"),
        Output("shade_edit", "value"),
        Output("water_edit", "value"),
        Output("required_eq_edit", "value"),
        Output("weather_edit", "value"),
        Output("crowdness_edit", "value"),
        Output("nearby_edit", "value"),
        Output("Entry_Fee_edit", "value"),
        Output("how_far_from_me_edit", "value"),
        Output("df_edit_store", "data"),
    ],
    [
        Input("trips_list_edit", "value"),
        Input("remove_btn_edit", "n_clicks"),
        Input("confirm_remove_trip_edit", "submit_n_clicks"),
        Input("update-btn_edit", "n_clicks"),
        Input("reset-btn_edit", "n_clicks"),
        Input("confirm_reset_edit", "submit_n_clicks"),
        Input("load_btn_edit", "n_clicks"),
        Input("apply-btn", "n_clicks"),
        Input("confirm_apply_trip_edit", "submit_n_clicks"),
        Input("kmh_edit", "value")
    ],
        State('df_edit_store', 'data'),
        State('load_clicks_store', 'data'),
        State("trip_name_edit", "value"),
        State("accessibility_edit", "value"),
        State("Season_edit", "value"),
        State("trail_length_edit","value"),
        State("circular_edit", "value"),
        State("kmh_edit", "value"),
        State("walkinghr_edit", "value"),
        State("challenge_edit", "value"),
        State("terrain_edit", "value"),
        State("view_edit", "value"),
        State("shade_edit", "value"),
        State("water_edit", "value"),
        State("required_eq_edit", "value"),
        State("weather_edit", "value"),
        State("crowdness_edit", "value"),
        State("nearby_edit", "value"),
        State("Entry_Fee_edit", "value"),
        State("how_far_from_me_edit", "value"),
)
def handle_update_tab(
    trip_name,remove_clicks,confirm_remove_clicks,update_clicks,reset_clicks,
    confirm_reset_clicks,load_clicks,apply_clicks,confirm_apply_clicks,kph,df_edit_data,
    load_n_clicks,trip_name_input,accessibility,season_edit,trail_length_edit,circular_is,kmh_edit,walkinghr,
    challenge,terrain,view,shade,water,required,weather,crowdness,nearby,entryfee,how_far
):

    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    # Work with a copy so we don't mutate the original
    df_edit = df_copy.copy()


    if not df_edit.empty and "Trip" in df_edit.columns:
        trips_list = df_edit["Trip"].unique().tolist()
        trip_options_edit = [{"label": t, "value": t} for t in trips_list]
        # If the chosen trip isn't in the DataFrame anymore, pick the first
        if trip_name not in trips_list:
            trip_name = trips_list[0] if trips_list else None
            
        # Initialize trip_name_value with the first item's value in trip_options_edit
        trip_name_value = None
    else:
        trip_options_edit = []
        trip_name = None
        trip_name_value = None

    # Identify which Input triggered the callback
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # ---------------------
    # Default "no update" placeholders
    # ---------------------
    modal_content = dash.no_update
    modal_open = False
    confirm_remove = dash.no_update
    confirm_reset = dash.no_update
    confirm_apply = dash.no_update
    accessibility_value = dash.no_update
    season_value = dash.no_update
    trail_length_value = dash.no_update
    circular_value = dash.no_update
    kmh_value = dash.no_update
    challenge_value = dash.no_update
    terrain_value = dash.no_update
    view_value = dash.no_update
    shade_value = dash.no_update
    water_value = dash.no_update
    required_eq_value = dash.no_update
    weather_value = dash.no_update
    crowdness_value = dash.no_update
    nearby_value = dash.no_update
    entry_fee_value = dash.no_update
    how_far_from_me_value = dash.no_update
    trips_count_content = dash.no_update
    trip_options_updated = dash.no_update
    trip_value_updated = dash.no_update
    walkinghr_value =""

    
    # Count summary if needed
    if not df_edit.empty:
        trips_count_content = f"""
        ### Trips Evaluation Count
        There are **{df_edit['Trip'].nunique()}** trips.
        """
    
    selected_trip = df_edit[df_edit["Trip"] == trip_name]
    row = selected_trip.iloc[0]  # one row            
    inc_row = row.get ("Incline","")
    dec_row = row.get("Decline","")

    distance_km = float(trail_length_edit) if trail_length_edit else 0
    pace_kph = float(kph) if kph else 0  # Default pace
    ascent_m = float(inc_row) if inc_row else 0
    descent_m = float(dec_row) if dec_row else 0

    if distance_km not in [None, ""] and distance_km > 0:
        if pace_kph not in [None, ""] and pace_kph > 0 :
           if ascent_m > 0 and descent_m >0: 
                v_kmh = float(pace_kph)
                walkinghr_value = naismith_rule(distance_km, ascent_m, descent_m, v_kmh)
        else:
            walkinghr_value = dash.no_update        
    print(walkinghr_value)        
        
        
    # -------------
    # LOAD TRIP
    # -------------
        
    if triggered_id == "load_btn_edit" and trip_name:
        df_load = load_data_from_gsheet()
        load_clicks = load_clicks + 1 if load_clicks else 1
        selected_trip = df_load[df_load["Trip"] == trip_name]
        if not selected_trip.empty:
            row = selected_trip.iloc[0]  # one row
            trip_name_value = row.get("Trip", "")
            accessibility_value = row.get("Accessibility", "")
            season_value = row.get("Season", "")
            trail_length_value = row.get("Trail Length", "")
            circular_value = row.get("Circular?", "")
            kmh_value = row.get("KMH", "")
            walkinghr_value = row.get("Walking Hours", "")
            challenge_value = row.get("Challenge", "")
            terrain_value = row.get("Terrain", "")
            view_value = row.get("View", "")
            shade_value = row.get("Shade", "")
            water_value = row.get("Water", "")
            required_eq_value = row.get("Required Equipment", "")
            weather_value = row.get("Weather", "")
            crowdness_value = row.get("Crowdness", "")
            nearby_value = row.get("Nearby Attractions", "")
            entry_fee_value = row.get("Entry Fee", "")
            how_far_from_me_value = row.get("Distance", "")

        return (
            modal_content,          # 1 - modal-body_edit.children
            modal_open,
            dash.no_update,         # 2 - trips_list_edit.options
            dash.no_update,         # 3 - trips_list_edit.value
            dash.no_update,         # 4 - trips_count_edit.children
            dash.no_update,         # 5 - confirm_remove_trip_edit.displayed
            dash.no_update,         # 6 - confirm_reset_edit.displayed
            dash.no_update,         # 7 - confirm_apply_trip_edit.displayed
            trip_name_value,        # 8 - trip_name_edit.value
            accessibility_value,    # 9 - accessibility_edit.value
            season_value,           # 10 - Season_edit.value
            trail_length_value,
            circular_value,         # 11 - circular_edit.value
            kmh_value,              # 12 - kmh_edit.value
            walkinghr_value,        # 13 - walkinghr_edit.value
            challenge_value,        # 14 - challenge_edit.value
            terrain_value,          # 15 - terrain_edit.value
            view_value,             # 16 - view_edit.value
            shade_value,            # 17 - shade_edit.value
            water_value,            # 18 - water_edit.value
            required_eq_value,      # 19 - required_eq_edit.value
            weather_value,          # 20 - weather_edit.value
            crowdness_value,        # 21 - crowdness_edit.value
            nearby_value,           # 22 - nearby_edit.value
            entry_fee_value,        # 23 - Entry_Fee_edit.value
            how_far_from_me_value,  # 24 - how_far_from_me_edit.value
            df_load.to_dict("records"),  # 25 - df_edit_store.data
        )
    elif triggered_id == 'apply-btn':       
        if load_clicks == 0 or not trip_name in df_edit["Trip"].values:
                modal_open = True
                modal_content = "Please select a trip to edit!"
                return (
                    modal_content,                                 # 1
                    modal_open,
                    dash.no_update,                                # 2 - updated options
                    dash.no_update,                                # 3 - updated value
                    dash.no_update,                                # 4 - trips_count_edit.children
                    False,                                         # 5 - close remove confirmation
                    False,                                         # 6 - close reset confirmation
                    False,                                         # 7 - close apply confirmation
                    dash.no_update,                                # 8
                    dash.no_update,                                # 9
                    dash.no_update,                                # 10
                    dash.no_update,
                    dash.no_update,                                # 11
                    dash.no_update,                                # 12
                    dash.no_update,                                # 13
                    dash.no_update,                                # 14
                    dash.no_update,                                # 15
                    dash.no_update,                                # 16
                    dash.no_update,                                # 17
                    dash.no_update,                                # 18
                    dash.no_update,                                # 19
                    dash.no_update,                                # 20
                    dash.no_update,                                # 21
                    dash.no_update,                                # 22
                    dash.no_update,                                # 23
                    dash.no_update,                                # 24
                    df_edit.to_dict("records"),                    # 25
                )
        else:
            # Replace dash.no_update with actual values
            modal_content = ""
            modal_open = False
            trips_count_edit_children = f"Total Trips: {len(trip_options_edit)}"
            confirm_apply_trip_edit_open = True

            return (
                modal_content,                                 # 1
                modal_open,
                dash.no_update,                                # 2 - updated options
                dash.no_update,                                # 3 - updated value
                dash.no_update,                                # 4 - trips_count_edit.children
                False,                                         # 5 - close remove confirmation
                False,                                         # 6 - close reset confirmation
                True,                                         # 7 - close apply confirmation
                dash.no_update,                                # 8
                dash.no_update,                                # 9
                dash.no_update,                                # 10
                dash.no_update,
                dash.no_update,                                # 11
                dash.no_update,                                # 12
                dash.no_update,                                # 13
                dash.no_update,                                # 14
                dash.no_update,                                # 15
                dash.no_update,                                # 16
                dash.no_update,                                # 17
                dash.no_update,                                # 18
                dash.no_update,                                # 19
                dash.no_update,                                # 20
                dash.no_update,                                # 21
                dash.no_update,                                # 22
                dash.no_update,                                # 23
                dash.no_update,                                # 24
                df_edit.to_dict("records"),                    # 25
            )
            
    elif triggered_id == 'confirm_apply_trip_edit':
        if confirm_apply_clicks:
            # Perform the update logic
            selected_trip = df_edit[df_edit["Trip"] == trip_name]
            
            if selected_trip.empty:
                # Handle case where trip is not found
                modal_content = "Selected trip not found."
                modal_open = True
                return (
                    modal_content,
                    modal_open,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    df_edit.to_dict("records"),
                )

            row_number = selected_trip.index[0] + 2  # Adjust for 1-based index and header row

            # Extract values for E:K (5th to 11th columns: Accessibility to Water)
            values_ek = [
                accessibility,     # From accessibility_edit input
                season_edit,       # From Season_edit input
                challenge,         # From challenge_edit input
                terrain,           # From terrain_edit input
                view,              # From view_edit input
                shade,             # From shade_edit input
                water              # From water_edit input
            ]
            row = selected_trip.iloc[0]  # one row
            area_row = row.get("Area", "")
            inc_row = row.get ("Incline","")
            inc_pre_row = row.get("Inc_Pre","")
            dec_row = row.get("Decline","")
            dec_pre_row = row.get("Dec_Pre","")
            # Safely convert values from Tab5 inputs
            area_val = area_scores.get(area_row,0)
            accessibility_value = Accessibility.get(accessibility, 0)
            season_value = Season.get(season_edit, 0)
            challenge_value = Challenge.get(challenge, 0)
            terrain_value = Terrain.get(terrain, 0)
            view_value = View.get(view, 0)
            shade_value = Shade.get(shade, 0)
            water_value = Water.get(water, 0)
            circular_value = circular.get(circular_is, 0)
            trail_length_value = trail_length_score(trail_length_edit)

            incline_val = incline_score(inc_row) 
            inc_pre = inc_precentage_score(inc_pre_row) 

            incline_deg = row.get("Incline Degree","")
            decline_val = decline_score(dec_row)
            dec_pre = dec_precentage_score(dec_pre_row)
            dec_deg = row.get("Decline Degree", "")
            kmh_value = kmh_validity(kmh_edit)
            walkinghr_value = walkinghr_scores(walkinghr)
            required_eq_value = Required_eq.get(required, 0)
            weather_value = Weather.get(weather, 0)
            crowdness_value = Crowdness.get(crowdness, 0)
            nearby_value = Nearby_attractions.get(nearby, 0)
            entry_fee_value = Entry_Fee.get(entryfee, 0)
            how_far_from_me_value = How_far_from_me.get(how_far, 0)
            
           # Recalculate Total Score independently
            score_total = weighted_scores(
                area_val, accessibility_value, season_value, challenge_value, terrain_value,
                view_value, shade_value, entry_fee_value, water_value, nearby_value,
                circular_value, trail_length_value, incline_val, decline_val,
                inc_pre, dec_pre, walkinghr_value, how_far_from_me_value,
                required_eq_value, weather_value, crowdness_value
            )
            # Extract values for T:AB (20th to 28th columns: KMH to Total Score)
            values_tab = [
                kmh_edit,          # From kmh_edit input
                walkinghr,         # From walkinghr_edit input
                required,          # From required_eq_edit input
                weather,           # From weather_edit input
                crowdness,         # From crowdness_edit input
                nearby,            # From nearby_edit input
                entryfee,          # From Entry_Fee_edit input
                how_far,           # From how_far_from_me_edit input
                score_total        # Use recalculated Total Score
            ]

            # Update the specific columns in Google Sheet
            update_row(SPREADSHEET_ID, row_number, values_ek, values_tab)

            # Reload the updated DataFrame
            df_updated = load_data_from_gsheet()

            # Prepare modal content
            modal_content = html.H2(f"'{trip_name}' has been successfully updated with a new Total Score!")
            modal_open = True

            # Prepare updated trips list and count
            if not df_updated.empty and "Trip" in df_updated.columns:
                trips_list_updated = df_updated["Trip"].unique().tolist()
                trip_options_edit_updated = [{"label": t, "value": t} for t in trips_list_updated]
                trips_count_content = f"### Trips Evaluation Count\nThere are **{len(trips_list_updated)}** trips."
            else:
                trip_options_edit_updated = []
                trips_count_content = "### Trips Evaluation Count\nNo trips available."

            return (
                modal_content,  # Output 1: modal-body_edit.children
                modal_open,     # Output 2: edit-modal_edit.is_open
                trip_options_edit_updated,  # Output 3: trips_list_edit.options
                trip_name,      # Output 4: trips_list_edit.value
                trips_count_content,  # Output 5: trips_count_edit.children
                False,          # Output 6: confirm_remove_trip_edit.displayed
                False,          # Output 7: confirm_reset_edit.displayed
                False,          # Output 8: confirm_apply_trip_edit.displayed
                "", # Output 9: trip_name_edit.value
                "", # Output 10: accessibility_edit.value
                "", # Output 11: Season_edit.value
                "", # Output 12: trail_length_edit.value
                "", # Output 13: circular_edit.value
                "", # Output 14: kmh_edit.value
                "", # Output 15: walkinghr_edit.value
                "", # Output 16: challenge_edit.value
                "", # Output 17: terrain_edit.value
                "", # Output 18: view_edit.value
                "", # Output 19: shade_edit.value
                "", # Output 20: water_edit.value
                "", # Output 21: required_eq_edit.value
                "", # Output 22: weather_edit.value
                "", # Output 23: crowdness_edit.value
                "", # Output 24: nearby_edit.value
                "", # Output 25: Entry_Fee_edit.value
                "", # Output 26: how_far_from_me_edit.value
                df_updated.to_dict("records"),  # Output 27: df_edit_store.data
            )
        else:
            raise dash.exceptions.PreventUpdate


        
    elif triggered_id == 'update-btn_edit':
        df_edit = load_data_from_gsheet()
            # Count summary if needed
        if not df_edit.empty:
            trips_count_content = f"""
            ### Trips Evaluation Count
            There are **{df_edit['Trip'].nunique()}** trips.
            """
            updated_trip_options = []
            updated_trip_value = None
            if not df_edit.empty:
                updated_trip_options = [
                    {"label": t, "value": t}
                    for t in df_edit["Trip"].unique()
                    
                ]
                updated_trip_value = df_edit["Trip"].iloc[0]
        modal_open = True
        modal_content = f"The DF has been updated!"
        return (
            modal_content,
            modal_open,
            updated_trip_options,                          # 2 - updated options
            updated_trip_value,                            # 3 - updated value
            trips_count_content,                           # 4 - trips_count_edit.children
            False,     
            dash.no_update,  # 6 - confirm_reset_edit.displayed
            dash.no_update,  # 7 - confirm_apply_trip_edit.displayed
            dash.no_update,  # 8 - trip_name_edit.value
            dash.no_update,  # 9 - accessibility_edit.value
            dash.no_update,  # 10 - Season_edit.value
            dash.no_update,
            dash.no_update,  # 11 - circular_edit.value
            dash.no_update,  # 12 - kmh_edit.value
            dash.no_update,  # 13 - walkinghr_edit.value
            dash.no_update,  # 14 - challenge_edit.value
            dash.no_update,  # 15 - terrain_edit.value
            dash.no_update,  # 16 - view_edit.value
            dash.no_update,  # 17 - shade_edit.value
            dash.no_update,  # 18 - water_edit.value
            dash.no_update,  # 19 - required_eq_edit.value
            dash.no_update,  # 20 - weather_edit.value
            dash.no_update,  # 21 - crowdness_edit.value
            dash.no_update,  # 22 - nearby_edit.value
            dash.no_update,  # 23 - Entry_Fee_edit.value
            dash.no_update,  # 24 - how_far_from_me_edit.value
            df_edit.to_dict("records"),  # 25 - df_edit_store.data
        )        
    # -------------
    # REMOVE BTN CLICKED -> show confirmation
    # -------------
    elif triggered_id == "remove_btn_edit":
        # Just trigger the confirmation dialog
        return (
            modal_content,      # 1
            modal_open,
            dash.no_update,     # 2
            dash.no_update,     # 3
            dash.no_update,     # 4
            True,               # 5 - open confirm_remove_trip_edit
            dash.no_update,     # 6
            dash.no_update,     # 7
            dash.no_update,     # 8
            dash.no_update,     # 9
            dash.no_update,     # 10
            dash.no_update,
            dash.no_update,     # 11
            dash.no_update,     # 12
            dash.no_update,     # 13
            dash.no_update,     # 14
            dash.no_update,     # 15
            dash.no_update,     # 16
            dash.no_update,     # 17
            dash.no_update,     # 18
            dash.no_update,     # 19
            dash.no_update,     # 20
            dash.no_update,     # 21
            dash.no_update,     # 22
            dash.no_update,     # 23
            dash.no_update,     # 24
            df_edit.to_dict("records"),  # 25
        )

    # -------------
    # CONFIRM REMOVE
    # -------------
    elif triggered_id == "confirm_remove_trip_edit":
        if trip_name and confirm_remove_clicks:
            # Remove from local df
            df_after_removal = df_edit[df_edit["Trip"] != trip_name]

            # Also remove from GSheet
            removed = remove_trip_from_gsheet(trip_name)
            if removed:
                modal_open = True
                modal_content = f"Trip '{trip_name}' has been successfully removed."
            else:
                modal_content = f"Failed to remove trip '{trip_name}'."

            # Recompute trips list/ count
            updated_trip_options = []
            updated_trip_value = None
            trips_count_content = ""
            if not df_after_removal.empty:
                updated_trip_options = [
                    {"label": t, "value": t}
                    for t in df_after_removal["Trip"].unique()
                ]
                updated_trip_value = df_after_removal["Trip"].iloc[0]
                trips_count_content = f"""
                ### Trips Evaluation Count
                There are **{df_after_removal['Trip'].nunique()}** trips.
                """
            else:
                # If everything is removed
                trips_count_content = "No trips left in the dataset."
            return (
                modal_content,                                 # 1
                modal_open,
                updated_trip_options,                          # 2 - updated options
                updated_trip_value,                            # 3 - updated value
                trips_count_content,                           # 4 - trips_count_edit.children
                False,                                         # 5 - close remove confirmation
                dash.no_update,                                # 6
                dash.no_update,                                # 7
                dash.no_update,                                # 8
                dash.no_update,                                # 9
                dash.no_update,                                # 10
                dash.no_update,
                dash.no_update,                                # 11
                dash.no_update,                                # 12
                dash.no_update,                                # 13
                dash.no_update,                                # 14
                dash.no_update,                                # 15
                dash.no_update,                                # 16
                dash.no_update,                                # 17
                dash.no_update,                                # 18
                dash.no_update,                                # 19
                dash.no_update,                                # 20
                dash.no_update,                                # 21
                dash.no_update,                                # 22
                dash.no_update,                                # 23
                dash.no_update,                                # 24
                df_after_removal.to_dict("records"),           # 25
            )
            
    elif triggered_id == 'reset-btn_edit':
        return (
                modal_content,                                 # 1
                modal_open,
                dash.no_update,                          # 2 - updated options
                dash.no_update,                            # 3 - updated value
                dash.no_update,                           # 4 - trips_count_edit.children
                False,                                        # 5 - close remove confirmation
                True,                                          # 6
                dash.no_update,                                # 7
                dash.no_update,                                # 8
                dash.no_update,                                # 9
                dash.no_update,                                # 10
                dash.no_update,
                dash.no_update,                                # 11
                dash.no_update,                                # 12
                dash.no_update,                                # 13
                dash.no_update,                                # 14
                dash.no_update,                                # 15
                dash.no_update,                                # 16
                dash.no_update,                                # 17
                dash.no_update,                                # 18
                dash.no_update,                                # 19
                dash.no_update,                                # 20
                dash.no_update,                                # 21
                dash.no_update,                                # 22
                dash.no_update,                                # 23
                dash.no_update,                                # 24
                df_edit.to_dict("records"),           # 25
            )
    elif triggered_id == 'confirm_reset_edit':
        clear_gsheet_except_headers()
        modal_content = "DataFrame (Google Sheet) cleared successfully."
        modal_open = True

        df_after_clear = load_data_from_gsheet()
        valid_score_count = df_after_clear['Trip'].nunique()
        cleared_trips_count_content = f"""
        ### Trips Evaluation Count
        There are **{valid_score_count}** trips.
        """
        # Check if the DataFrame is empty or missing the "Trip" column
        if "Trip" in df_after_clear.columns:
            if not df_after_clear.empty:
                # Modify the first row of the "Trip" column
                df_after_clear.at[0, "Trip"] = None
            else:
                # Add a row if the DataFrame is empty
                df_after_clear = pd.DataFrame(columns=["Trip"])
                df_after_clear.loc[0] = [None]
        else:
            # If the "Trip" column is missing, create it
            df_after_clear["Trip"] = None
            df_after_clear.loc[0, "Trip"] = None

        print("DataFrame after modification:")
        print(df_after_clear)

        # No data => empty dropdown
        cleared_trips_options = []
        cleared_trip_value = df_after_clear["Trip"].iloc[0] = None
        
        return (
                modal_content,                                 # 1
                modal_open,
                cleared_trips_options,                          # 2 - updated options
                cleared_trip_value,                            # 3 - updated value
                cleared_trips_count_content,                    # 4 - trips_count_edit.children
                False,                                        # 5 - close remove confirmation
                False,                                          # 6
                dash.no_update,                                # 7
                dash.no_update,                                # 8
                dash.no_update,                                # 9
                dash.no_update,                                # 10
                dash.no_update,
                dash.no_update,                                # 11
                dash.no_update,                                # 12
                dash.no_update,                                # 13
                dash.no_update,                                # 14
                dash.no_update,                                # 15
                dash.no_update,                                # 16
                dash.no_update,                                # 17
                dash.no_update,                                # 18
                dash.no_update,                                # 19
                dash.no_update,                                # 20
                dash.no_update,                                # 21
                dash.no_update,                                # 22
                dash.no_update,                                # 23
                dash.no_update,                                # 24
                df_after_clear.to_dict("records"),           # 25
            )             
    # -------------
    # DEFAULT NO-OP
    # -------------
    return (
        dash.no_update,  # 1 - modal_content
        dash.no_update,
        dash.no_update,  # 2 - trips_list_edit.options
        dash.no_update,  # 3 - trips_list_edit.value
        dash.no_update,  # 4 - trips_count_edit.children
        dash.no_update,  # 5 - confirm_remove_trip_edit.displayed
        dash.no_update,  # 6 - confirm_reset_edit.displayed
        dash.no_update,  # 7 - confirm_apply_trip_edit.displayed
        dash.no_update,  # 8 - trip_name_edit.value
        dash.no_update,  # 9 - accessibility_edit.value
        dash.no_update,  # 10 - Season_edit.value
        dash.no_update,
        dash.no_update,  # 11 - circular_edit.value
        dash.no_update,  # 12 - kmh_edit.value
        walkinghr_value,  # 13 - walkinghr_edit.value
        dash.no_update,  # 14 - challenge_edit.value
        dash.no_update,  # 15 - terrain_edit.value
        dash.no_update,  # 16 - view_edit.value
        dash.no_update,  # 17 - shade_edit.value
        dash.no_update,  # 18 - water_edit.value
        dash.no_update,  # 19 - required_eq_edit.value
        dash.no_update,  # 20 - weather_edit.value
        dash.no_update,  # 21 - crowdness_edit.value
        dash.no_update,  # 22 - nearby_edit.value
        dash.no_update,  # 23 - Entry_Fee_edit.value
        dash.no_update,  # 24 - how_far_from_me_edit.value
        df_edit.to_dict("records"),  # 25 - df_edit_store.data
    )

# Define the main layout with tabs
app.layout = html.Div(
    [
        dcc.Tabs(id='tabs', value='tab1', children=[
                dcc.Tab(
                    label='Trips Stats ',
                    children=tab1_layout(),
                    style=tab_style,
                    selected_style=selected_tab_style,
                    value='tab1'
                ),
                dcc.Tab(
                    label='Trips Filtering',
                    children=tab3_layout(),
                    style=tab_style,
                    selected_style=selected_tab_style,
                    value='tab3'
                ),
                dcc.Tab(
                    label='Trips Dashboard',
                    children=tab4_layout(),
                    style=tab_style,
                    selected_style=selected_tab_style,
                    value='tab4'
                ),
                dcc.Tab(
                    label='Trips Calculation',
                    children=tab2_layout(),
                    style=tab_style,
                    selected_style=selected_tab_style,
                    value='tab2'
                ),
                dcc.Tab(
                    label='Trips Editor',
                    children=tab5_layout(),
                    style=tab_style,
                    selected_style=selected_tab_style,
                    value='tab5'
                ),
            ],
        ),
    ]
)


if __name__ == "__main__":
    app.run_server(host='100.74.93.47', port=8050, debug=True)