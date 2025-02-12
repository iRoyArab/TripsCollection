import os
import re
import pandas as pd
import dash
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from dash import html, Input, Output
from dash import dcc
from dash import dash_table
from dash.dash_table import DataTable
import dash.exceptions as dash_exceptions



import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import ast
import math
import gpxpy 
import gpxpy.gpx


from pathlib import Path
from dash import dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate




# Initialize the app
csv_file_path = "Trip_Collection.csv"
if not os.path.exists(csv_file_path):
    # If the file doesn't exist, create it with the default columns
    df_global = pd.DataFrame(columns=[
        "Trip", "Coordinates", "Trail Link" "Area", "Accessibility","Season", "Challenge",
        "Terrain", "View", "Shade", "Water","Circular?", "Trail Length", "Incline", "Inc_Pre", "Incline Degree", "Decline", "Dec_Pre", "Decline Degree","KMH", "Walking Hours","Required Equipment",
        "Weather", "Crowdness", "Nearby Attractions", "Entry Fee", "Distance", "Total Score"
    ])
    df_global.to_csv(csv_file_path, index=True)
else:
    df_global = pd.read_csv(csv_file_path,index_col=0)


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "The Trip Collection"




def compute_valid_score_count (df):
    if not df.empty:
        if "Total Score" in df:
            scores = pd.to_numeric(df["Total Score"], errors='coerce')
            valid_score_count = scores[scores.notnull()].count()
        else:
            valid_score_count = 0
    else:
        valid_score_count=0
    return valid_score_count



"""
Trips Calculation

------------------------------------------------------------------------------------------------------------------------------------------------

"""

def trip_name_val(trip, df):
    if not trip:
        raise ValueError("Please insert a valid trip name.")
    elif os.path.exists(csv_file_path):
            if not df.empty:    
                if trip in df["Trip"].values:
                    raise ValueError("This trip is already in the data!")
    return trip

def mid_trail_coordinate(coord,link,season, df):
    if not coord:
        raise ValueError("Please insert a coordinate!")
    elif "," not in coord:
        raise ValueError("Invalid coordinate string, a comma is missing")  
    elif os.path.exists(csv_file_path):
            if not df.empty:  
                if coord in df["Coordinates"].values :
                    if link in df.loc[df["Coordinates"] == coord]["Trail Link"].values and season in df.loc[df["Coordinates"] == coord]["Trail Link"].values:
                        raise ValueError("This coordinate is already in another trip!")
    return coord

def link_validity (link,df):
    if not link:
        raise ValueError("Please insert a valid link address.")
    elif not "https://israelhiking.osm.org.il/share/" in link:
        raise ValueError("Please insert a valid link!")     
    return link
    
    
def float_to_duration(value):
    hours = int(value)  # Extract the hours
    minutes = round((value - hours) * 60)  # Calculate the minutes
    return f"{hours:02d}:{minutes:02d}"  # Format as HH:MM

def duration_to_int(duration):
    hours, minutes = map(int, duration.split(":"))  # Split the duration string into hours and minutes
    return hours + minutes / 60  # Convert to float representing the total hours


def naismith_rule(distance_km, ascent_m, descent_m, pace_kph):

    # Base walking time (time for distance only)
    base_time = distance_km / pace_kph
    avg_rest_time = base_time/5
    # Elevation adjustment (1 hour for every 600 meters of ascent)
    ascent_time = ascent_m / 600.0
    descent_time = descent_m / 1800.0
    # Total time
    total_time = base_time + ascent_time + descent_time + avg_rest_time
    hr = float_to_duration(total_time)
    return hr

 
def is_decimal_number(input_value):
    # Check if input is not a string and is a numeric type
    return isinstance(input_value, float) and not isinstance(input_value, (str, bool))

# Dictionaries for scoring
area_scores = {
    "Golan Heights - North-East Galilee": 10,
    "Golan Heights": 9.5,
    "Upper Galilee": 9.25,
    "Western Galilee": 9.2,
    "Galilee Center & The Kinerret":9,
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

Shade= {
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
"High, mendatory and nothing special":0
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

"""Trail_length = {
"10KM, an average of 4-5 walking hours": 10,
"7-9KM, an average of 3.5-4.5 walking hours": 9,
"5-7KM, an average of 2.5-3.5 walking hours": 7.5,
"14-15KM, extensive daytrip, an average of 6-7 walking hours": 7,
"3-5KM, an average of 1.5-2.5 walking hours": 6,
"19-20KM, a full day of walking, about 8-9 walking hours": 5.5,
"Higher than 20KM, more than 9 walking hours": 4,
"2-3KM, about 1 walking hours": 2,
"1-2KM, less than half an hour": 0
}"""


def trail_length_score(trail_length):
    # Attempt to convert to float if the input is a string
    try:
        trail_length = float(trail_length)
    except (ValueError, TypeError):
        raise ValueError("Please insert a valid decimal number for the trail length.")

    # Validate the range
    if trail_length < 1 or trail_length > 25:
        raise ValueError("Not a relevant trail length, sorry :(")

    # Determine the score
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
    elif 2 <= trail_length < 3:
        return 2
    elif 1 <= trail_length < 2:
        return 1
    # Default fallback (should not occur)
    return 0
 
circular= {
     "Yes": 10,
     "No": 0
 }

def incline_score (incline):
    try:
        incline = int(incline)
    except (ValueError, TypeError):
        raise ValueError("Please insert a valid number for the incline.")
        # Validate the range
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
    elif 1200 < incline <=2500:
        return 2.5
    elif 1 <= incline < 150:
        return 2
    # Default fallback (should not occur)
    return 0

def decline_score (decline):
    try:
        decline = int(decline)
    except (ValueError, TypeError):
        raise ValueError("Please insert a valid number for the decline.")
        # Validate the range
    if decline < -2500 or decline > 1:
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
    elif 1200 < decline <=2500:
        return 2.5
    elif 1 <= decline < 150:
        return 2
    # Default fallback (should not occur)
    return 0 

def inc_precentage_score(incline_pre):
     if not incline_pre:
         raise ValueError("Please enter an incline precentage of the trail")
     elif 40 < incline_pre <=50:
         return 10
     elif 50 < incline_pre <=60:
         return 9
     elif 60 < incline_pre <=70:
         return 8
     elif 30 <= incline_pre <=40:
         return 7
     elif 70 < incline_pre <=80: 
         return 6
     elif 80 < incline_pre <=90:
         return 5
     elif 90 < incline_pre <=100:
         return 4
     elif 20 <= incline_pre <30:
         return 3
     elif 10 <= incline_pre <20:
         return 2
     elif 0<= incline_pre < 10:
         return 1
     else:
         0   

def dec_precentage_score(decline_pre):
     if not decline_pre:
         raise ValueError("Please enter an incline precentage of the trail")
     elif 50 <= decline_pre <60:
         return 10
     elif 40 <= decline_pre <50:
         return 9
     elif 30 <= decline_pre <40:
         return 8
     elif 60 <= decline_pre <=70:
         return 7
     elif 20 <= decline_pre <30:
         return 6
     elif 10 <= decline_pre <20:
         return 5
     elif 0 <= decline_pre <10:
         return 4
     elif 70 < decline_pre <=80:
         return 3
     elif 80 < decline_pre <90:
         return 2
     elif 90 < decline_pre <=100:
         return 1
     else:
        0                
def kmh_validity(kmh):
    # Check if kmh is provided
    if kmh is None or kmh == '':
        raise ValueError("Please enter an average KMH")
    try:
        kmh_float = float(kmh)
    except ValueError:
        raise ValueError("Please insert a valid decimal number for kmh.")

    if kmh_float <= 0 or kmh_float >= 15:
        raise ValueError("Invalid kmh input! Must be greater than 0 and less than 15.")

    return kmh_float

def walkinghr_scores(whr):
    if not whr:
        raise ValueError("Please provide a travel time in the format 'hh:mm'")
    try:
        # Split the input into hours and minutes
        hours, minutes = map(int, whr.split(":"))
    except ValueError:
        raise ValueError("Invalid format. Please provide time in 'hh:mm' format.")

    # Convert to decimal hours
    whr_value = hours + minutes / 60

    # Determine the score based on ranges
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
    else:
        # Fallback case for unexpected inputs
        raise ValueError("Unexpected input. Ensure the time is within a valid range.")      
    
           
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
    "background-image": "url('https://media.istockphoto.com/id/688429288/photo/its-not-an-experience-if-you-cant-share-it.jpg?s=2048x2048&w=is&k=20&c=Tc71AeWSJBXqAWI4Xbji5eXNvCt1cNj0yUyBrBhlXiE=')",
    "background-size": "cover",
    "background-position": "top",
    "background-repeat": "no-repeat",
    'color': 'white',
    'border-color': 'white',
    'font-size': '24px',
    
}

selected_tab_style = {
    "background-color": "rgba(255, 255, 255, 0.5)",
    "background-image": "url('https://w0.peakpx.com/wallpaper/466/460/HD-wallpaper-nature-mountain-forest-landscape-fog-winter-snow-ultra-for-your-mobile-tablet-explore-mountain-northern-lights-nature-snowy-forest-landscape.jpg')",
    "background-size": "cover",
    "background-position": "top",
    'color': 'white',
    'font-size': '24px',
    'font-weight': 'bold',
    'border-color': 'red',
}

heading_style = {
    "text-align": "center",
    "font-family": "Arial, sans-serif",
    "color": "#2C3E50",
    "margin-bottom": "20px",
}

card_style={
   "background-image": "url('https://www.pixelstalk.net/wp-content/uploads/2016/08/Black-Backgrounds-HD-1920x1080-For-Desktop.jpg')" 
}

button_style = {
    "width": "40%",
    "height": "80px",
    "margin": "750px auto auto -450px",
    "background-color": "#3498DB",
    "color": "black",
    "border": "2px solid black",
    "display": "block",
    "font-weight": "bold",
}

button_style1 = {
    "width": "26%",
    "height": "60px",
    "margin": "10px ",
    "background-color": "green",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "left",
}

button_style_2 = {
    "width": "30%",
    "height": "60px",
    "margin": "-50px 0px auto 700px",
    "background-color": "red",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "yellow",
    "textAlign": "center",
    "display": "block",
}

button_style3 = {
    "width": "26%",
    "height": "60px",
    "margin": "50px 0 50px auto ",
    "background-color": "orange",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center",
}

button_style4 = {
    "width": "56%",
    "height": "60px",
    "margin": "-60px auto 500px 450px ",
    "background-color": "orange",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center",
}

button_style6 ={
    "width": "36%",
    "height": "60px",
    "margin": "25px 20px 70px  ",
    "background-color": "orange",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center"
}

button_style7 = {
    "width": "26%",
    "height": "60px",
    "margin": "25px 20px 70px  ",
    "background-color": "red",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center"    
}

button_style8 = {
    "width": "26%",
    "height": "60px",
    "margin": "25px 20px 70px  ",
    "background-color": "orange",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center"    
}

button_style9 = {
    "width": "26%",
    "height": "60px",
    "margin": "25px 20px 70px  ",
    "background-color": "green",
    "border": "2px solid black",
    "font-weight": "bold",
    "color": "white",
    "textAlign": "center"    
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

def tab1_layout():
    return html.Div(
        style=background_style,
        children=[
            dcc.Interval(id='interval-component', interval=1 * 1000, n_intervals=0),
            dcc.Store(id='df-store'),  # Store to hold DataFrame data
            dcc.Store(id='default-values', data={
                'trip': "",
                'mid_trail_coordinate': "",
                "trail_link":"",
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
                'declinedg':"",
                'kmh':"",
                'walkinghr':"",
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
                                        children="### Trip Evaluation Count\nThere are **0** trips.",
                                        style={'fontSize': '24px', 'marginTop': '100px', 'textAlign': 'left'}
                                    ),
                                    html.Br(),
                                    dcc.Markdown(
                                        id='Remove_trip',
                                        children="### Remove a trip",
                                        style={'fontSize': '24px', 'marginTop': '20px', 'textAlign': 'left'}
                                    ),
                                    dcc.Dropdown(
                                        id='trips_list',
                                        options=[],
                                        value= None,
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
                                                dbc.Label("Elevation:",style={'justify-content':'center'}),
                                                html.Br(),
                                                html.Div([
                                                    dbc.Label("Up:", style={"margin-right": "10px"}),  # Add spacing between label and input
                                                    dcc.Input(id='incline', type='text', value="", className="form-control", style={"display": "inline-block", "width": "45%"}, disabled=True),
                                                    dbc.Label("Down:", style={"margin-left": "20px", "margin-right": "10px"}),  # Adjust margin for spacing
                                                    dcc.Input(id='decline', type='text', value="", className="form-control", style={"display": "inline-block", "width": "45%"}, disabled=True)
                                                ], style={"display": "flex", "align-items": "center", "justify-content": "space-between"}),
                                                html.Br(),
                                                html.Div([
                                                    dcc.Input(id='percentagein', type='text', value="", className="form-control", style={"display": "inline-block", "width": "45%","margin-left": "30px"}, disabled=True),
                                                    dbc.Label("%:", style={"margin-left": "10px", "margin-right": "10px"}),  # Adjust margin for spacing
                                                    dcc.Input(id='percentagede', type='text', value="", className="form-control", style={"display": "inline-block", "width": "45%","margin-left": "30px" }, disabled=True),
                                                    dbc.Label("%:", style={"margin-left": "10px"}),  # Add spacing between label and input
                                                ], style={"display": "flex", "align-items": "center", "justify-content": "space-between"}),
                                                html.Br(),
                                                html.Div([
                                                    dcc.Input(id='inclinedg', type='text', value="", className="form-control", style={"display": "inline-block", "width": "65%","margin-left": "30px"}, disabled=True),
                                                    dbc.Label("°", style={"margin-left": "10px", "margin-right": "10px"}),  # Adjust margin for spacing
                                                    dcc.Input(id='declinedg', type='text', value="", className="form-control", style={"display": "inline-block", "width": "65%","margin-left": "30px"}, disabled=True),
                                                    dbc.Label("°", style={"margin-left": "10px", "margin-right": "10px"})  # Add spacing between label and input
                                                ], style={"display": "flex", "align-items": "center", "justify-content": "space-between"}),
                                        ]),
                                                html.Br(),
                                                dbc.Label("Estimated Travel Time:"),
                                                html.Br(),
                                                    dbc.Label("Enter your average km/h speed:"),  # Add spacing between label and input
                                                    dcc.Input(id='kmh', type='text', value="", className="form-control", style={"display": "inline-block", "width": "45%"}),
                                                    dbc.Label("KM/H", style={"margin-left": "10px"}),
                                                    html.Br(),
                                                dcc.Input(id='walkinghr', type='text', value="", className="form-control", style={"display": "inline-block", "width": "45%",}, disabled=True),
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
                                ],width=4,
                            )
                        ]
                    )
                ]
            )
        ]
    )

def exclude_empty_all_na(df):
    """
    Exclude columns that are entirely empty or contain only NA values.
    """
    return df.dropna(axis=1, how='all')

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
        Output("Season","value"),
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
        Output("kmh", "value"),  # Added this output to reset kmh to default
        Output('incline', 'disabled'),
        Output('decline', 'disabled'),
        Output('percentagein', 'disabled'),
        Output('percentagede', 'disabled'),
        Output("walkinghr","disabled"),
        Output("decline","value"),
        Output("declinedg","value"),
        Output("inclinedg","value"),
        Output("percentagein","value"),
        Output("percentagede","value"),
        Output("walkinghr","value")  
    ],
    [
        Input("calculate-btn", "n_clicks"),
        Input('circular', 'value'),
        Input("confirm_remove_trip", "submit_n_clicks"),
        Input("remove_btn", "n_clicks"),
        Input("confirm_reset", "submit_n_clicks"),
        Input("reset-btn", "n_clicks"),
        Input("incline","value"),
        Input("decline","value"),
        Input("percentagein","value"),
        Input("kmh","value"),
        Input('interval-component', 'n_intervals')
    ],
    [
        State("trip_name", "value"),
        State("coordinate", "value"),
        State("trail_link", "value"),
        State("area", "value"),
        State("accessibility", "value"),
        State("Season","value"),
        State("challenge", "value"),
        State("terrain", "value"),
        State("view", "value"),
        State("shade", "value"),
        State("water", "value"),
        State("required_eq", "value"),
        State("circular","value"),
        State("trail_length", "value"),
        State("incline","value"),
        State("decline","value"),
        State("inclinedg","value"), 
        State("declinedg","value"),
        State("percentagein","value"),
        State("percentagede","value"),
        State("kmh","value"),
        State("walkinghr","value"),              
        State("weather", "value"),
        State("crowdness", "value"),
        State("nearby", "value"),
        State("Entry_Fee", "value"),
        State("how_far_from_me", "value"),
        State("trips_list", "value"),
        State("default-values", "data")
    ],
    prevent_initial_call=True 
)
def update_tab1(calculate_clicks, circular_input, confirm_remove_trip, remove_clicks, confirm_reset,
                reset_clicks, incline_value, decline_input, precentagein_input, kmh_input, n_intervals,
                trip_name, coordinate,trail_link, area, accessibility, season, challenge, terrain, view, shade, water,
                required_eq, circular, trail_length, inc, dec, incdeg, decdeg, incpre, decpre, kmh, walkinghours,
                weather, crowdness, nearby, entry_fee, how_far_from_me, trips_list_value, defaults):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
    

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

    trp = trips_list_value

    # Read CSV
    if os.path.exists(csv_file_path):
        if os.path.getsize(csv_file_path) > 0:
            df = pd.read_csv(csv_file_path, index_col=0)
        else:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

    if not df.empty:
        trips_list = df["Trip"].to_list()
        trips_options = [{'label': trip, 'value': trip} for trip in df["Trip"].unique()]
        
        if trips_list:
            if trp in trips_list:
                trip_value = trp  # Keep current selection
            else:
                trip_value = trips_list[0]  # Select first if current not available
        else:
            trip_value = None
    else:
        trips_options = []
        trip_value = None

    # Update the trip count
    valid_score_count = compute_valid_score_count(df)
    trip_count_content = f"""  
    ### Trips Evaluation Count
    There are **{valid_score_count}** trips.
    """

    circular_scores = {
        "Yes": 10,
        "No": 0
    }

    # Validate trail_length
    valid_trail_length = False
    if trail_length is not None:
        try:
            trail_length_num = float(trail_length)
            if 1 < trail_length_num <= 25:
                valid_trail_length = True
        except ValueError:
            pass

    # Set incline_disabled and decline_disabled based on circular_input
    if circular_input == "Yes":
        incline_disabled = False
        decline_disabled = True
        percentagein_disabled = True
        percentagede_disabled = True
        whr_disabled = True

        if incline_value not in [None, ""]:
            try:
                incline_value_num = float(incline_value)
                decline_output = 0 - incline_value_num
                decs_value = float(-decline_output)
                percentagein_value = 50
                percentagede_value = 50
                if valid_trail_length:
                    initial_cal = math.atan(incline_value_num / (trail_length_num * 1000 / 2))
                    inclinedg_value = round(math.degrees(initial_cal),4)
                    declinedg_value = -inclinedg_value
                    if kmh_input not in [None, ""]:
                        v_kmh= float(kmh_input)
                        v_trln = float(trail_length)
                        walkinghr_value= naismith_rule(v_trln,incline_value_num,(decs_value),v_kmh)
                    else:
                        walkinghr_value=dash.no_update
            except ValueError:
                decline_output = ""
        else:
            decline_output = ""
    elif circular_input == "No":
        incline_disabled = False
        decline_disabled = False
        percentagein_disabled = False
        percentagede_disabled = False
        whr_disabled = True
        percentagein_value = ""
        percentagede_value = ""

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

        if valid_trail_length:
            try:
                if incline_value not in [None, ""]:
                    incline_value_num = float(incline_value)
                    percentagein_val = float(percentagein_value) if percentagein_value != "" else 0
                    initial_cal = math.atan(incline_value_num / (trail_length_num * 1000 * (percentagein_val/100))) if percentagein_val > 0 else 0
                    inclinedg_value = math.degrees(initial_cal)
                else:
                    inclinedg_value = ""

                if decline_input not in [None, ""]:
                    decline_value_num = float(decline_input)
                    percentagede_val = float(percentagede_value) if percentagede_value != "" else 0
                    initial_cal_2 = math.atan(decline_value_num / (trail_length_num * 1000 * (percentagede_val/100))) if percentagede_val > 0 else 0
                    declinedg_value = math.degrees(initial_cal_2)
                else:
                    declinedg_value = ""

                if incline_value not in [None, ""] and decline_input not in [None, ""]:
                    incline_value_num = float(incline_value)
                    decline_value_num = -float(decline_input)
                    if kmh_input not in [None, ""]:
                        v_kmh= float(kmh_input)
                        v_trln = float(trail_length)
                        walkinghr_value= naismith_rule(v_trln,incline_value_num,decline_value_num,v_kmh)
                    else:
                        walkinghr_value=dash.no_update
                else:
                    if inclinedg_value == "" and declinedg_value == "":
                        walkinghr_value = dash.no_update
            except ValueError:
                inclinedg_value = ""
                declinedg_value = ""
                walkinghr_value = dash.no_update
    else:
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

    # Handle triggers
    if triggered_id == 'interval-component':
        # Just update trip count and do not reset user inputs
        if not df.empty:
            trips_list = df["Trip"].to_list()
            trips_options = [{'label': trip, 'value': trip} for trip in df["Trip"].unique()]
            
            if trips_list:
                if trp in trips_list:
                    trip_value = trp
                else:
                    trip_value = trips_list[0]
            else:
                trip_value = None
        else:
            trips_options = []
            trip_value = None

        valid_score_count = compute_valid_score_count(df)
        trip_count_content = f"""  
        ### Trips Evaluation Count
        There are **{valid_score_count}** trips.
        """

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
            walkinghr_value
        )

    elif triggered_id == "reset-btn" and reset_clicks > 0:
        confirm_reset_displayed = True
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
            walkinghr_value
        )

    elif triggered_id == "confirm_reset" and confirm_reset > 0:
        # Handle confirm reset
        if os.path.exists(csv_file_path) and not df.empty:
            df = pd.DataFrame()
            df.to_csv(csv_file_path, index=True)
            modal_content = html.Div("DataFrame cleared successfully.")
            modal_is_open = True
            valid_score_count = compute_valid_score_count(df)
            trip_count_content = f"""
            ### Trips Evaluation Count
            There are **{valid_score_count}** trips.
            """ 
            trips_options = []
            trip_value = None
            return (
                    modal_content,                 # "modal-body", "children"
                    modal_is_open,                 # "score-modal", "is_open"
                    confirm_reset_displayed,       # "confirm_reset", "displayed"
                    trip_count_content,            # 'trips_count', 'children'
                    confirm_remove_trip_displayed, # "confirm_remove_trip", "displayed"
                    trips_options,                 # "trips_list", "options"
                    trip_value,                    # "trips_list", "value"

                    # Resetting all fields to defaults:
                    defaults["trip"],             # "trip_name", "value"
                    defaults["mid_trail_coordinate"], # "coordinate", "value"
                    defaults["trail_link"],
                    defaults["area_scores"],       # "area", "value"
                    defaults["Accessibility"],     # "accessibility", "value"
                    defaults["Season"],
                    defaults["Challenge"],         # "challenge", "value"
                    defaults["terrain"],           # "terrain", "value"
                    defaults["view"],              # "view", "value"
                    defaults["shade"],             # "shade", "value"
                    defaults["water"],             # "water", "value"
                    defaults["trail_length"],      # "trail_length", "value"
                    defaults["circular"],          # "circular", "value"
                    defaults["required_eq"],       # "required_eq", "value"
                    defaults["weather"],           # "weather", "value"
                    defaults["crowdness"],         # "crowdness", "value"
                    defaults["nearby_attractions"],# "nearby", "value"
                    defaults["Entry_Fee"],         # "Entry_Fee", "value"
                    defaults["how_far_from_me"],   # "how_far_from_me", "value"
                    defaults["kmh"],               # "kmh", "value"
                    
                    incline_disabled,              # 'incline', 'disabled'
                    decline_disabled,              # 'decline', 'disabled'
                    percentagein_disabled,         # 'percentagein', 'disabled'
                    percentagede_disabled,         # 'percentagede', 'disabled'
                    whr_disabled,                  # "walkinghr","disabled"
                    defaults["incline"],
                    defaults["decline"],           # "decline","value"
                    defaults["declinedg"],         # "declinedg","value"
                    defaults["inclinedg"],         # "inclinedg","value"
                    defaults["percentagein"],       # "percentagein","value"
                    defaults["percentagede"],       # "percentagede","value"
                    defaults["walkinghr"]           # "walkinghr","value"
                )
        modal_content = "No Data to Clear."
        modal_is_open = True
        valid_score_count = compute_valid_score_count(df)
        trip_count_content = f"""
        ### Trips Evaluation Count
        There are **{valid_score_count}** trips.
        """ 
        return (
                modal_content,                 # "modal-body", "children"
                modal_is_open,                 # "score-modal", "is_open"
                confirm_reset_displayed,       # "confirm_reset", "displayed"
                trip_count_content,            # 'trips_count', 'children'
                confirm_remove_trip_displayed, # "confirm_remove_trip", "displayed"
                trips_options,                 # "trips_list", "options"
                trip_value,                    # "trips_list", "value"

                # Resetting all fields to defaults:
                defaults["trip"],             # "trip_name", "value"
                defaults["mid_trail_coordinate"], # "coordinate", "value"
                defaults["trail_link"],
                defaults["area_scores"],       # "area", "value"
                defaults["Accessibility"],     # "accessibility", "value"
                defaults["Season"],
                defaults["Challenge"],         # "challenge", "value"
                defaults["terrain"],           # "terrain", "value"
                defaults["view"],              # "view", "value"
                defaults["shade"],             # "shade", "value"
                defaults["water"],             # "water", "value"
                defaults["trail_length"],      # "trail_length", "value"
                defaults["circular"],          # "circular", "value"
                defaults["required_eq"],       # "required_eq", "value"
                defaults["weather"],           # "weather", "value"
                defaults["crowdness"],         # "crowdness", "value"
                defaults["nearby_attractions"],# "nearby", "value"
                defaults["Entry_Fee"],         # "Entry_Fee", "value"
                defaults["how_far_from_me"],   # "how_far_from_me", "value"
                defaults["kmh"],               # "kmh", "value"
                
                incline_disabled,              # 'incline', 'disabled'
                decline_disabled,              # 'decline', 'disabled'
                percentagein_disabled,         # 'percentagein', 'disabled'
                percentagede_disabled,         # 'percentagede', 'disabled'
                whr_disabled,                  # "walkinghr","disabled"
                defaults["incline"],
                defaults["decline"],           # "decline","value"
                defaults["declinedg"],         # "declinedg","value"
                defaults["inclinedg"],         # "inclinedg","value"
                defaults["percentagein"],       # "percentagein","value"
                defaults["percentagede"],       # "percentagede","value"
                defaults["walkinghr"]           # "walkinghr","value"
            )

    elif triggered_id == "remove_btn" and remove_clicks > 0:
        confirm_remove_trip_displayed = True
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
            walkinghr_value
        )

    elif triggered_id == "confirm_remove_trip" and confirm_remove_trip > 0:
        # Handle remove trip confirmation
        if trp is None:
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
                walkinghr_value
            )

        if os.path.exists(csv_file_path) and not df.empty:
            if trp in df["Trip"].values:
                df = df[df["Trip"] != trp]
                df.to_csv(csv_file_path, index=True)
                
                df_filtered = exclude_empty_all_na(df)
                trips_list = df_filtered["Trip"].to_list()
                trips_options = [{'label': trip, 'value': trip} for trip in df_filtered["Trip"].unique()]
                
                if trips_list:
                    if trp in trips_list:
                        trip_value = trp
                    else:
                        trip_value = trips_list[0]
                else:
                    trip_value = None

                valid_score_count = compute_valid_score_count(df_filtered)
                trip_count_content = f"""  
                ### Trips Evaluation Count
                There are **{valid_score_count}** trips.
                """
                modal_content = f"Trip '{trip_name}' has been removed."
                modal_is_open = True
            return (
                    modal_content,                 # "modal-body", "children"
                    modal_is_open,                 # "score-modal", "is_open"
                    confirm_reset_displayed,       # "confirm_reset", "displayed"
                    trip_count_content,            # 'trips_count', 'children'
                    confirm_remove_trip_displayed, # "confirm_remove_trip", "displayed"
                    trips_options,                 # "trips_list", "options"
                    trip_value,                    # "trips_list", "value"

                    # Resetting all fields to defaults:
                    defaults["trip"],             # "trip_name", "value"
                    defaults["mid_trail_coordinate"], # "coordinate", "value"
                    defaults["trail_link"],
                    defaults["area_scores"],       # "area", "value"
                    defaults["Accessibility"],     # "accessibility", "value"
                    defaults["Season"],
                    defaults["Challenge"],         # "challenge", "value"
                    defaults["terrain"],           # "terrain", "value"
                    defaults["view"],              # "view", "value"
                    defaults["shade"],             # "shade", "value"
                    defaults["water"],             # "water", "value"
                    defaults["trail_length"],      # "trail_length", "value"
                    defaults["circular"],          # "circular", "value"
                    defaults["required_eq"],       # "required_eq", "value"
                    defaults["weather"],           # "weather", "value"
                    defaults["crowdness"],         # "crowdness", "value"
                    defaults["nearby_attractions"],# "nearby", "value"
                    defaults["Entry_Fee"],         # "Entry_Fee", "value"
                    defaults["how_far_from_me"],   # "how_far_from_me", "value"
                    defaults["kmh"],               # "kmh", "value"
                    
                    incline_disabled,              # 'incline', 'disabled'
                    decline_disabled,              # 'decline', 'disabled'
                    percentagein_disabled,         # 'percentagein', 'disabled'
                    percentagede_disabled,         # 'percentagede', 'disabled'
                    whr_disabled,                  # "walkinghr","disabled"
                    defaults["incline"],
                    defaults["decline"],           # "decline","value"
                    defaults["declinedg"],         # "declinedg","value"
                    defaults["inclinedg"],         # "inclinedg","value"
                    defaults["percentagein"],       # "percentagein","value"
                    defaults["percentagede"],       # "percentagede","value"
                    defaults["walkinghr"]           # "walkinghr","value"
                )

        modal_content = f"Trip '{trip_name}' not found in data."
        modal_is_open = True
        return (
                modal_content,                 # "modal-body", "children"
                modal_is_open,                 # "score-modal", "is_open"
                confirm_reset_displayed,       # "confirm_reset", "displayed"
                trip_count_content,            # 'trips_count', 'children'
                confirm_remove_trip_displayed, # "confirm_remove_trip", "displayed"
                trips_options,                 # "trips_list", "options"
                trip_value,                    # "trips_list", "value"

                # Resetting all fields to defaults:
                defaults["trip"],             # "trip_name", "value"
                defaults["mid_trail_coordinate"], # "coordinate", "value"
                defaults["trail_link"],
                defaults["area_scores"],       # "area", "value"
                defaults["Accessibility"],     # "accessibility", "value"
                defaults["Season"],                
                defaults["Challenge"],         # "challenge", "value"
                defaults["terrain"],           # "terrain", "value"
                defaults["view"],              # "view", "value"
                defaults["shade"],             # "shade", "value"
                defaults["water"],             # "water", "value"
                defaults["trail_length"],      # "trail_length", "value"
                defaults["circular"],          # "circular", "value"
                defaults["required_eq"],       # "required_eq", "value"
                defaults["weather"],           # "weather", "value"
                defaults["crowdness"],         # "crowdness", "value"
                defaults["nearby_attractions"],# "nearby", "value"
                defaults["Entry_Fee"],         # "Entry_Fee", "value"
                defaults["how_far_from_me"],   # "how_far_from_me", "value"
                defaults["kmh"],               # "kmh", "value"
                
                incline_disabled,              # 'incline', 'disabled'
                decline_disabled,              # 'decline', 'disabled'
                percentagein_disabled,         # 'percentagein', 'disabled'
                percentagede_disabled,         # 'percentagede', 'disabled'
                whr_disabled,                  # "walkinghr","disabled"
                defaults["incline"],
                defaults["decline"],           # "decline","value"
                defaults["declinedg"],         # "declinedg","value"
                defaults["inclinedg"],         # "inclinedg","value"
                defaults["percentagein"],       # "percentagein","value"
                defaults["percentagede"],       # "percentagede","value"
                defaults["walkinghr"]           # "walkinghr","value"
            )

    elif triggered_id == "calculate-btn" and calculate_clicks > 0:
        try:
            scores = {
                "Trip": trip_name_val(trip_name, df),
                "Coordinates": mid_trail_coordinate(coordinate,trail_link,season, df),
                "Trail Link": link_validity(trail_link,df),
                "Area": area_scores.get(area, 0),
                "Accessibility": Accessibility.get(accessibility, 0),
                "Season": Season.get(season,0),
                "Challenge": Challenge.get(challenge, 0),
                "Terrain": Terrain.get(terrain, 0),
                "View": View.get(view, 0),
                "Shade": Shade.get(shade, 0),
                "Entry Fee": Entry_Fee.get(entry_fee, 0),
                "Water": Water.get(water, 0),
                "Nearby Attractions": Nearby_attractions.get(nearby, 0),
                "Circular?": circular_scores.get(circular, 0),
                "Trail Length": trail_length_score(trail_length),
                "Incline": incline_score(inc),
                "Incline Percentage": inc_precentage_score(incpre),
                "Incline Degree": incdeg,
                "Decline": decline_score(dec),
                "Decline Precentage": dec_precentage_score(decpre),
                "Decline Degree": decdeg,
                "KM Per Hour": kmh_validity(kmh),
                "Walking Hours": walkinghr_scores(walkinghours),
                "How Far?": How_far_from_me.get(how_far_from_me, 0),
                "Required EQ": Required_eq.get(required_eq, 0),
                "Weather": Weather.get(weather, 0),
                "Crowdness": Crowdness.get(crowdness, 0)
            }

            weighted_scores = {
                "Area": scores["Area"] * 0.1,
                "Accessibility": scores["Accessibility"] * 0.05,
                "Season": scores["Season"] * 0.03,
                "Challenge": scores["Challenge"] * 0.08,
                "Terrain": scores["Terrain"] * 0.075,
                "View": scores["View"] * 0.01,
                "Shade": scores["Shade"] * 0.075,
                "Entry Fee": scores["Entry Fee"] * 0.025,
                "Water": scores["Water"] * 0.05,
                "Nearby Attractions": scores["Nearby Attractions"] * 0.05,
                "Circular?": scores["Circular?"] * 0.05,
                "Trail Length": scores["Trail Length"] * 0.075,
                "Incline": scores["Incline"] * 0.02,
                "Decline": scores["Decline"] * 0.015,
                "Incline Percentage": scores["Incline Percentage"] * 0.015,
                "Decline Percentage": scores["Decline Precentage"] * 0.01,
                "Walking Hours": scores["Walking Hours"] * 0.025,
                "How Far?": scores["How Far?"] * 0.075,
                "Required EQ": scores["Required EQ"] * 0.075,
                "Weather": scores["Weather"] * 0.04,
                "Crowdness": scores["Crowdness"] * 0.05
            }

            total_score = sum(weighted_scores.values())

            labels = [
        "Trip", "Coordinates","Trail Link", "Area", "Accessibility","Season", "Challenge",
        "Terrain", "View", "Shade", "Water","Circular?", "Trail Length", "Incline","Inc_Pre",
        "Incline Degree", "Decline","Dec_Pre", "Decline Degree", "KMH", "Walking Hours","Required Equipment",
        "Weather", "Crowdness", "Nearby Attractions", "Entry Fee", "Distance", "Total Score"
            ]            
            values = [
                trip_name, coordinate,trail_link, area, accessibility,season, challenge, terrain, view,
                shade, water,circular, trail_length, inc,incpre,incdeg, dec,decpre,decdeg,
                kmh, walkinghours, required_eq, weather,
                crowdness, nearby, entry_fee, how_far_from_me, total_score
            ]

            # Append to CSV
            if os.path.exists(csv_file_path):
                if os.path.getsize(csv_file_path) > 0:
                    df_existing = pd.read_csv(csv_file_path, index_col=0)
                    new_row = pd.DataFrame([values], columns=labels)
                    
                    df_existing_filtered = exclude_empty_all_na(df_existing)
                    new_row_filtered = exclude_empty_all_na(new_row)
                    
                    df_combined = pd.concat([df_existing_filtered, new_row_filtered], ignore_index=True)
                    df_combined.to_csv(csv_file_path, index=True)
                else:
                    df_new = pd.DataFrame([values], columns=labels)
                    df_new.to_csv(csv_file_path, index=True)
            else:
                df_new = pd.DataFrame([values], columns=labels)
                df_new.to_csv(csv_file_path, index=True)
                
            df = pd.read_csv(csv_file_path, index_col=0)
            df_filtered = exclude_empty_all_na(df)

            valid_score_count = compute_valid_score_count(df_filtered)
            trip_count_content = f"""  
            ### Trips Evaluation Count
            There are **{valid_score_count}** checked trips.
            """
            
            trips_list = df_filtered["Trip"].to_list()
            trips_options = [{'label': trip, 'value': trip} for trip in df_filtered["Trip"].unique()]

            if trips_list:
                if trp in trips_list:
                    trip_value = trp
                else:
                    trip_value = trips_list[0]
            else:
                trip_value = None
                
            modal_content = html.Div([
                html.H2(f"Total Score: {total_score}"),
                html.Ul([html.Li(f"{key}: {val}") for key, val in scores.items()])
            ])
            modal_is_open = True

            return (
                modal_content,                 # "modal-body", "children"
                modal_is_open,                 # "score-modal", "is_open"
                confirm_reset_displayed,       # "confirm_reset", "displayed"
                trip_count_content,            # 'trips_count', 'children'
                confirm_remove_trip_displayed, # "confirm_remove_trip", "displayed"
                trips_options,                 # "trips_list", "options"
                trip_value,                    # "trips_list", "value"

                # Resetting all fields to defaults:
                defaults["trip"],             # "trip_name", "value"
                defaults["mid_trail_coordinate"], # "coordinate", "value"
                defaults["trail_link"],                
                defaults["area_scores"],       # "area", "value"
                defaults["Accessibility"],     # "accessibility", "value"
                defaults['Season'],
                defaults["Challenge"],         # "challenge", "value"
                defaults["terrain"],           # "terrain", "value"
                defaults["view"],              # "view", "value"
                defaults["shade"],             # "shade", "value"
                defaults["water"],             # "water", "value"
                defaults["trail_length"],      # "trail_length", "value"
                defaults["circular"],          # "circular", "value"
                defaults["required_eq"],       # "required_eq", "value"
                defaults["weather"],           # "weather", "value"
                defaults["crowdness"],         # "crowdness", "value"
                defaults["nearby_attractions"],# "nearby", "value"
                defaults["Entry_Fee"],         # "Entry_Fee", "value"
                defaults["how_far_from_me"],   # "how_far_from_me", "value"
                defaults["kmh"],               # "kmh", "value"
                
                incline_disabled,              # 'incline', 'disabled'
                decline_disabled,              # 'decline', 'disabled'
                percentagein_disabled,         # 'percentagein', 'disabled'
                percentagede_disabled,         # 'percentagede', 'disabled'
                whr_disabled,                  # "walkinghr","disabled"
                defaults["decline"],           # "decline","value"
                defaults["declinedg"],         # "declinedg","value"
                defaults["inclinedg"],         # "inclinedg","value"
                defaults["percentagein"],       # "percentagein","value"
                defaults["percentagede"],       # "percentagede","value"
                defaults["walkinghr"]           # "walkinghr","value"
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
            walkinghr_value
        )

    # Default return if none of the above conditions match
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
        walkinghr_value
    )





def tab2_layout():

    # If CSV exists and has data, read it to get initial min/max for the RangeSliders
    if os.path.exists(csv_file_path) and os.path.getsize(csv_file_path) > 0:
        df = pd.read_csv(csv_file_path, index_col=0)
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
    else:
        # If CSV doesn't exist or is empty, just build a minimal layout
        df = pd.DataFrame()
        markers_israel = []

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
            dcc.Interval(id='interval-analysis', interval=1 * 1000, n_intervals=0),
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
                                        'width': '630px',
                                        'height': '680px',
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
        Input('interval-analysis', 'n_intervals'),
        Input("length_slider", "value"),
        Input("score_slider", "value"),
        Input("trip_picker", "n_clicks"),
    ],
    State("trips_list_2", "value"),
    prevent_initial_call=True
)
def update_tab2(n_intervals, length_value, score_value, n_clicks, trips_list_value):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    # Read CSV if available
    if os.path.exists(csv_file_path):
        if os.path.getsize(csv_file_path) > 0:
            df = pd.read_csv(csv_file_path, index_col=0)
        else:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

    # Prepare default (fallback) returns for an empty df
    markers_israel = []
    link_trail_src = dash.no_update
    trip_details_div = dash.no_update

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
    min_length = float(df["Trail Length"].min())
    max_length = float(df["Trail Length"].max())
    min_score = float(df["Total Score"].min())
    max_score = float(df["Total Score"].max())

    # Ensure length_value and score_value are lists [low, high] and in correct range
    if not length_value or len(length_value) < 2:
        length_value = [min_length, max_length]
    else:
        # clamp them if out of range
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
            "column": "Chellenge",
            "rank_list": [
                "Very Challenging, with Lots of Obstacles in The Way",
                "There's Some Challenge, but Most of it is in Average Challenge",
                "There's some challenge, but Most of The Trail is Easy",
                "Medium Challenge",
                "Easy-Medium",
                "Easy",
                "No Challenge At All!"
            ],
            "display_name": "Chellenge",
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
    higest_score = filtered_df["Total Score"].max()
    trip_hs = filtered_df.loc[filtered_df["Total Score"] == higest_score, 'Trip'].iloc[0]
    common_view = filtered_df["View"].mode().iloc[0]
    common_distance = filtered_df["Distance"].mode().iloc[0]
    common_area = filtered_df["Area"].mode().iloc[0]
    check_trips = compute_valid_score_count(filtered_df)
    avg_len = round(filtered_df["Trail Length"].mean(), 5)

    # average walking time
    dur_list = filtered_df["Walking Hours"].tolist()
    whr_values = []
    for duration in dur_list:
        hours, minutes = map(int, duration.split(":"))
        whr_values.append(hours + minutes / 60)
    avg_time_int = sum(whr_values) / len(whr_values) if whr_values else 0
    avg_time = float_to_duration(avg_time_int)

    # Determine "most challenging trip"
    # We create a numerical rank if you have a more complex logic. For demonstration:
    filtered_df["Challenge Rank"] = filtered_df["Challenge"].apply(
        lambda x: challenge_mapping["Most Challenging"]["rank_list"].index(x)
        if x in challenge_mapping["Most Challenging"]["rank_list"] else 999
    )

    # sort to find top
    filtered_df_sorted = filtered_df.sort_values(
        by=["Challenge Rank", "Trail Length", "Incline Degree", "Decline Degree"],
        ascending=[True, False, False, True]
    )
    top_trip = filtered_df_sorted.iloc[0]["Trip"]
    top_incline_degree = filtered_df_sorted.iloc[0]["Incline Degree"]

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

    # --------------- If triggered by the interval (auto refresh) --------------- #
    if triggered_id == 'interval-analysis':
        score_value = dash.no_update
        length_value = dash.no_update
        # We basically just return the updated states
        return (
            markers_israel,                            # Israel-map-layer
            f"{trip_hs} : {higest_score}",             # highest_score
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

    # --------------- If triggered by the trip_picker --------------- #
    elif triggered_id == "trip_picker":
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
                    "opacity": "100%",
                },
            )

            return (
                markers_israel,
                f"{trip_hs} : {higest_score}",
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
                f"{trip_hs} : {higest_score}",
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

    # If anything else triggered, do nothing special
    raise PreventUpdate

def tab3_layout():
    csv_file_path = "Trip_Collection.csv"
    if os.path.exists(csv_file_path):
        if os.path.getsize(csv_file_path) > 0:
            # Load the DataFrame
            df = pd.read_csv(csv_file_path, index_col=0)

            # Extract columns for the `columns` dropdown
            cols = df.columns[3:11].tolist() + df.columns[21:-1].tolist()
            default_column = cols[0]  # Default to the first column in the list

            return html.Div(
                style=background_style4,
                children=[
                    dcc.Interval(id='interval-filtering', interval=1 * 1000, n_intervals=0),
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
                                                value=default_column,
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
                            dbc.Row([
                                dbc.Col(
                                    [
                                        html.Div(
                                            dash_table.DataTable(
                                                id='selected_trips',
                                                columns=[],  # Columns will be dynamically added
                                                data=[],     # Data will be dynamically added
                                                row_selectable='single',
                                                style_table={
                                                    'maxHeight': '400px',
                                                    'maxWidth': '1300px',
                                                    'overflowY': 'auto',
                                                    'overflowX': 'auto',
                                                    'margin': '10px auto',
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
                                            style={
                                                'margin': '0px 0px 0px 0x',
                                                'padding': '20px',
                                                'width': '1300px',
                                                'height': '450px',
                                                'backgroundColor': '',
                                                'opacity': '100%',
                                                'border': '1px solid #444',
                                                'borderRadius': '5px',
                                            }),
                                        html.Br(),
                                        dbc.Button("Reset All Filters", id='reset_filters', color='success', n_clicks=0, style=button_style7),
                                        dbc.Button("Add To Comparison", id='comp_trip', color='success', n_clicks=0, style=button_style9),
                                        
                                        html.H2("Trips Comparison"),
                                        html.Div(
                                            dash_table.DataTable(
                                                id='multi_trips_selection',
                                                columns=[],  # Columns will be dynamically added
                                                data=[],     # Data will be dynamically added
                                                style_table={
                                                    'maxHeight': '400px',
                                                    'maxWidth': '2450px',
                                                    'overflowY': 'auto',
                                                    'overflowX': 'auto',
                                                    'margin': '10px auto',
                                                },
                                                style_cell={
                                                    'textAlign': 'center',
                                                    'padding': '10px',
                                                    'minWidth': '150px',
                                                    'width': '150px',
                                                    'maxWidth': '300px',
                                                    'overflow': 'visible',  # Allow full text visibility
                                                    'whiteSpace': 'normal', # Ensure text wraps properly
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
                                                'backgroundColor': '',
                                                'opacity': '100%',
                                                'border': '1px solid #444',
                                                'borderRadius': '5px',
                                            }),
                                        html.Br(),
                                        dbc.Button("Clear Table", id='reset_table', color='success', n_clicks=0, style=button_style8),

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
                                            "margin": "0px 0px 0px -350px",  # Adjusted margin: top, right, bottom, left
                        
                                            
                                        },
                                    ),
                                    width=4
                                )
                            ]),
                        ]
                    )
                ]
            )
        else:
            return 'No DF'
    else:
        return "No DF"


@app.callback(
    [
        Output('col_sub', 'options'),
        Output('col_sub', 'value'),  # Add an output for resetting the sub_options selection
        Output('columns', 'value'),
    ],
    [
        Input('columns', 'value'),
        Input('reset_filters', 'n_clicks'),
        Input('interval-filtering','n_intervals')
    ]
)
def update_sub_filter_options(selected_column,n_intervals, n_clicks):
    csv_file_path = "Trip_Collection.csv"
    ctx = dash.callback_context

    # Check if CSV file exists and is not empty
    if os.path.exists(csv_file_path) and os.path.getsize(csv_file_path) > 0:
        df = pd.read_csv(csv_file_path, index_col=0)

        # Handle initial load or no trigger
        if not ctx.triggered:
            # Populate dropdown with default columns during initial layout
            default_columns = [{'label': str(value), 'value': value} for value in df[selected_column].dropna().unique()]
            return default_columns, "", selected_column

        # Determine which input triggered the callback
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if triggered_id == 'interval-filtering':
            if os.path.exists(csv_file_path) and os.path.getsize(csv_file_path) > 0:
                df = pd.read_csv(csv_file_path, index_col=0)
                selected_column = dash.no_update              
                sub_options = dash.no_update 
                return selected_column,sub_options, dash.no_update         
        # Reset filter logic
        elif triggered_id == 'reset_filters':
            if selected_column == 'Area':
                sub_options = [{'label': str(value), 'value': value} for value in df[selected_column].dropna().unique()]
                return sub_options, "", 'Area'  # Reset sub_options selection to ""
            else:
                default_columns = df.columns[3:11].tolist() + df.columns[21:-1].tolist()
                selected_column = 'Area'
                sub_options = [{'label': str(value), 'value': value} for value in df[selected_column].dropna().unique()]
                return sub_options, "", 'Area'

        # Generate sub-options based on selected column
        elif triggered_id == 'columns' and selected_column in df.columns:
            sub_options = [{'label': str(value), 'value': value} for value in df[selected_column].dropna().unique()]
            return sub_options, "", selected_column

    # Default return (empty options)
    return [], "", ""


@app.callback(
    [
        Output('selected_trips', 'columns'),
        Output('selected_trips', 'data'),
        Output('picked_trek_map', 'src'),  # Update the iframe
        Output('multi_trips_selection', 'columns'),
        Output('multi_trips_selection', 'data'),
    ],
    [
        Input('columns', 'value'),
        Input('col_sub', 'value'),
        Input('global-search', 'value'),
        Input('selected_trips', 'selected_rows'),
        Input('comp_trip', 'n_clicks'),
        Input('reset_table', 'n_clicks')
    ],
    [
        State('multi_trips_selection', 'data')
    ]
)
def display_filtered_trips(columns, col_sub, global_search, selected_rows, compare_clicks, reset_clicks, multi_trips_data):
    csv_file_path = "Trip_Collection.csv"
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    if not os.path.exists(csv_file_path) or os.path.getsize(csv_file_path) == 0:
        return [], [], "", [], []

    # Read the CSV file
    df4 = pd.read_csv(csv_file_path)

    # Apply Global Search Filter (if user typed something)
    if global_search:
        df4 = df4[df4.apply(
            lambda row: row.astype(str).str.contains(global_search, case=False).any(),
            axis=1
        )]

    # Apply Column-based Filter (if a valid column is chosen and sub-filter is not empty)
    if columns in df4.columns[3:-1].tolist() and col_sub:
        df4 = df4[df4[columns] == col_sub]

    if "Total Score" in df4.columns:
        df4 = df4.sort_values(by="Total Score", ascending=False)

    # Define columns for the selected_trips DataTable
    if not df4.empty:
        selected_trips_columns = [
            {'name': 'Trip', 'id': 'Trip'},
            {'name': columns, 'id': columns},
            {'name': 'Total Score', 'id': 'Total Score'},
            {'name': 'Trail Link', 'id': 'Trail Link'},
        ]

        # Convert the DataFrame to dictionary for DataTable
        selected_trips_data = df4[['Trip', columns, 'Total Score', 'Trail Link']].to_dict('records')

        # Handle row selection safely
        selected_trip_link = ""
        if selected_rows and len(selected_rows) > 0:
            selected_row_index = selected_rows[0]
            if selected_row_index < len(df4):  # Ensure the index is within bounds
                selected_trip_link = df4.iloc[selected_row_index]['Trail Link']
            
            if triggered_id == 'comp_trip' and compare_clicks > 0:
                # Add selected row to multi_trips_selection
                selected_row = df4.iloc[selected_row_index][
                    ['Trip', 'Area', 'Accessibility', 'Challenge', 'View', 'Shade', 'Water', 'Walking Hours', "Circular?", 'Distance', 'Total Score']
                ]
                selected_row_dict = selected_row.to_dict()
                if selected_row_dict not in multi_trips_data:  # Avoid duplicate rows
                    multi_trips_data = multi_trips_data or []  # Ensure it's a list if None
                    multi_trips_data.append(selected_row_dict)

        # Define columns for the multi_trips_selection DataTable
        multi_trips_columns = [
            {'name': col, 'id': col} for col in ['Trip', 'Area', 'Accessibility', 'Challenge', 'View', 'Shade', 'Water', 'Walking Hours', "Circular?", 'Distance', 'Total Score']
        ]

        if triggered_id == 'reset_table' and reset_clicks > 0:
            multi_trips_data = []

        return selected_trips_columns, selected_trips_data, selected_trip_link, multi_trips_columns, multi_trips_data

    # Return empty data if no rows match the filters
    return [], [], "", [], []




# Define create_histogram at the global level
def create_histogram(df):
    hist_data = np.histogram(df['Trail Length'], bins=5)
    bin_edges = hist_data[1]
    bin_counts = hist_data[0]

    colors = px.colors.qualitative.Prism_r
    fig = go.Figure()

    for i in range(len(bin_counts)):
        fig.add_trace(go.Bar(
            x=[(bin_edges[i] + bin_edges[i + 1]) / 2],
            y=[bin_counts[i]],
            width=[bin_edges[i + 1] - bin_edges[i]],
            marker_color=colors[i % len(colors)],
            text=[bin_counts[i]],
            textposition='outside',
            name=f'Bin {i + 1}'
        ))

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
        xaxis=dict(title=dict(text='Trail Length (in KM)', font=dict(size=22)), tickfont=dict(size=22)),
        yaxis=dict(title=dict(text='Count', font=dict(size=22)), tickfont=dict(size=22), range=[0, bin_counts.max() + 2]),
        barmode='overlay',
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )

    fig.update_traces(textfont=dict(size=28),hoverlabel=dict(font=dict(size=28)))
    return fig

def create_scatter_plot(df5):
    # Filter out rows with missing values for the regression calculation

    # Filter out rows with missing values
    filtered_data = df5.dropna(subset=['Walking Hours (hours)', 'Total Score'])
    
    # Sort the data by x-values (Walking Hours) to ensure a smooth line
    sorted_data = filtered_data.sort_values(by='Walking Hours (hours)')
    x_values = sorted_data['Walking Hours (hours)']
    y_values = sorted_data['Total Score']

    # Create the scatter plot
    fig = px.scatter(
        df5,
        x='Walking Hours (hours)',
        y='Total Score',
        title='Total Score vs Walking Hours (Hours)',
        labels={'Walking Hours (hours)': 'Walking Hours (Hours)','Total Score': 'Total Score'},
        color_discrete_sequence=['orange']
    )
    fig.update_traces(
        marker=dict(size=12),
        textfont=dict(size=28), # Font size for scatter point labels
        hoverlabel=dict(
            font=dict(size=22)  # Font size for hover labels
        )                
    )
    # Add the regression line
    fig.add_scatter(
        x=x_values,
        y=y_values,
        mode='lines',
        name='Connecting Line',
        line=dict(color='blue', dash='solid')
    )

    # Update layout for clarity and styling
    fig.update_layout(
        title=dict(font=dict(size=32)),
        xaxis_title='Walking Hours (Hours)',
        yaxis_title='Total Score',
        plot_bgcolor="rgba(0,0,0,0)",  # Transparent plot background
        paper_bgcolor="rgba(0,0,0,0)", # Transparent overall chart background
        showlegend=False,
        font=dict(size=22),  # Set font size for all text elements except title
        xaxis=dict(title=dict(font=dict(size=22)), tickfont=dict(size=22)),
        yaxis=dict(title=dict(font=dict(size=22)), tickfont=dict(size=22)),
        hoverlabel=dict(
            font=dict(size=22) 
    )
    )

    return fig

    
def tab4_layout():
    csv_file_path = "Trip_Collection.csv"

    if not os.path.exists(csv_file_path) or os.path.getsize(csv_file_path) == 0:
        return [], [], ""
    else:
        # Read the CSV file
        df5 = pd.read_csv(csv_file_path)
        df_sorted = df5.sort_values(by='Total Score', ascending=False)
        df_sorted=df_sorted.head(20)
        # Create the bar chart
        bar_chart1 = px.bar(
            df_sorted,
            x='Trip',
            y='Total Score',
            color = 'Total Score',
            color_discrete_sequence=px.colors.qualitative.Bold  # Use the 'bold' color palette
        )

        # Add values to each bar
        bar_chart1.update_traces(
            text=round(df_sorted['Total Score'],3),
            textposition='outside'
        )

                # Adjust the layout to remove the color scale and set font sizes
        bar_chart1.update_layout(
            font=dict(size=24),  # Set global font size
            yaxis=dict(
                range=[0, df_sorted['Total Score'].max() + 1],
                title=dict(text="Total Score", font=dict(size=22)),  # Y-axis title font size
                tickfont=dict(size=18),  # Y-axis tick font size
                tick0=0,  # Starting tick value
                dtick=0.5,
            ),
            xaxis=dict(
                title=dict(text="Trip", font=dict(size=22)),  # X-axis title font size
                tickfont=dict(size=18)  # X-axis tick font size
            ),
            title=dict(text="Top 20 Trips by Total Score", font=dict(size=32)),  # Chart title font size
            coloraxis_showscale=False,  # Disable the color scale
            showlegend=False,  # Hide the legend
            width=1200,  # Set chart width
            height=800,  # Set chart height
            plot_bgcolor="rgba(0,0,0,0)",  # Transparent plot background
            paper_bgcolor="rgba(0,0,0,0)", # Transparent overall chart background
            hoverlabel=dict(font=dict(size=20 ))
        )

        df_grouped = df5.groupby('Season')['Trip']
        df_pie = df_grouped.value_counts().reset_index()
        df_pie.columns = ['Season','Trip','Count']
        
        pie_chart1 = px.pie(df_pie, 
             names='Season', 
             values='Count', 
             title='Travelled Season', 
             color_discrete_sequence=px.colors.qualitative.Plotly, 
             hole=0.0)  # Optional for donut chart
    
        
        pie_chart1.update_layout(
            font=dict(size=18),
            title=dict(font=dict(size=32)),
            width=720,  # Set chart width
            height=800, 
            plot_bgcolor="rgba(0,0,0,0)",  # Transparent background inside the plot area
            paper_bgcolor="rgba(0,0,0,0)",
            hoverlabel=dict(font=dict(size=20 ))
            )
        
        pie_chart1.update_traces(
            textfont=dict(size=24)
        )
        
        
        area_df= df5['Area'].value_counts().reset_index()
        area_df.columns=['Area','Count']
        pie_chart2 = px.pie(area_df, 
             names='Area', 
             values='Count', 
             title='Trips by Area', 
             color_discrete_sequence=px.colors.qualitative.Prism_r, 
             hole=0.0)  # Optional for donut chart
    
        
        pie_chart2.update_layout(
            font=dict(size=18),
            title=dict(font=dict(size=32)),
            width=870,  # Set chart width
            height=800, 
            plot_bgcolor="rgba(0,0,0,0)",  # Transparent background inside the plot area
            paper_bgcolor="rgba(0,0,0,0)",
            hoverlabel=dict(font=dict(size=20 ))
            )
        
        pie_chart2.update_traces(
            textfont=dict(size=24)
        )
        
        
        
        df_length = df5.sort_values(by='Trail Length', ascending=False)
        df_length = df_length.head(20)
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
            textposition='outside'
        )
        bar_chart2.update_layout(
            font=dict(size=24),
            yaxis=dict(
                range=[0, df_length['Trail Length'].max() + 1],
                title=dict(text="Trail Length", font=dict(size=22)),
                tickfont=dict(size=18),
                tick0=0,
                dtick=1
            ),
            xaxis=dict(
                title=dict(text="Trip", font=dict(size=22)),
                tickfont=dict(size=18)
            ),
            title=dict(text="Top 20 Trips by Trail Length", font=dict(size=32)),
            coloraxis_showscale=False,
            showlegend=False,
            width=1200,
            height=800,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            hoverlabel=dict(font=dict(size=20))
        )

        
        df5['Walking Hours (hours)'] = df5['Walking Hours'].str.split(':').apply(
            lambda x: round(int(x[0]) + int(x[1]) / 60, 2) if isinstance(x, list) and len(x) == 2 else None
        )


        df5['Total Score'] = pd.to_numeric(df5['Total Score'], errors='coerce')

        def create_histogram(df5):
            # Calculate histogram data
            hist_data = np.histogram(df5['Trail Length'], bins=5)
            bin_edges = hist_data[1]
            bin_counts = hist_data[0]

            # Define colors for each bin
            colors = px.colors.qualitative.Prism_r

            # Create the figure
            fig = go.Figure()

            # Add histogram bars with different colors for each bin
            for i in range(len(bin_counts)):
                fig.add_trace(go.Bar(
                    x=[(bin_edges[i] + bin_edges[i + 1]) / 2],  # Bin center
                    y=[bin_counts[i]],
                    width=[bin_edges[i + 1] - bin_edges[i]],  # Bin width
                    marker_color=colors[i % len(colors)],
                    text=[bin_counts[i]],  # Add the bin value
                    textposition='outside',  # Position text above the bar
                    name=f'Bin {i + 1}',
                    hovertext=f'Bin {i + 1}: {bin_counts[i]}',  # Customize hover text
                    hoverinfo='text'  # Use the hovertext property for hover info
                ))

            # Add a line over the bins
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            fig.add_trace(go.Scatter(
                x=bin_centers,
                y=bin_counts,
                mode='lines+markers',
                line=dict(color='black', width=2),
                name='Frequency Line'
            ))

            # Update layout with font size adjustments
            fig.update_layout(
                title=dict(
                    text='Histogram of Trail Length',
                    font=dict(size=32)  # Font size for title
                ),
                xaxis=dict(
                    title=dict(
                        text='Trail Length (in KM)',
                        font=dict(size=22)  # Font size for x-axis title
                    ),
                    tickfont=dict(size=22)  # Font size for x-axis ticks
                ),
                yaxis=dict(
                    dtick=0.5,
                    title=dict(
                        text='Count',
                        font=dict(size=22),
                    ),
                    tickfont=dict(size=22),
                    range=[0, bin_counts.max() + 2]
                ),

                barmode='overlay',  # Overlay bars for seamless display
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)",  # Transparent plot background
                paper_bgcolor="rgba(0,0,0,0)",
                hoverlabel=dict(
                    font=dict(size=22)  # Font size for hover labels
                )
            )

            return fig
        # Generate plots as variables
        histogram_plot = create_histogram(df5)
        scatter_plot = create_scatter_plot(df5)



        return html.Div(
            style=background_style4,
            children=[
                dcc.Interval(id='interval-dashboard', interval=1 * 1000, n_intervals=0),
                dcc.Store(id='trip-dashboard-store'),
                dbc.Container(
                    style=container_style,
                    children=[
                        html.H1("Trips Dashboard", style=heading_style),
                        html.Hr(),
                        dbc.Row([
                            dbc.Col(
                                dcc.Graph(id='area_pie',figure=pie_chart2)
                            ),
                            dbc.Col(
                                dcc.Graph(id='length_hist',figure=histogram_plot)
                            ),
                            dbc.Col(
                                dcc.Graph(id='season_pie',figure=pie_chart1)
                            ),
                        ]),
                        dbc.Row([
                            dbc.Col(
                                dcc.Graph(id='length_chart',figure=bar_chart2)
                            ),

                            dbc.Col(
                                dcc.Graph(id='trips_chart',figure=bar_chart1)
                            ),
                        ]),
                        dbc.Row(
                            dbc.Col(
                                    dcc.Graph(id='scatter_plot',figure=scatter_plot)
                                )
                        )
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
    ],
    [Input('interval-dashboard', 'n_intervals')]
)
def update_figures(n_intervals):
    csv_file_path = "Trip_Collection.csv"

    if not os.path.exists(csv_file_path) or os.path.getsize(csv_file_path) == 0:
        raise dash.exceptions.PreventUpdate  # Prevent updating if file does not exist or is empty

    # Reload the CSV file
    df_c = pd.read_csv(csv_file_path)
    df_c['Walking Hours (hours)'] = df_c['Walking Hours'].str.split(':').apply(
        lambda x: round(int(x[0]) + int(x[1]) / 60, 2) if isinstance(x, list) and len(x) == 2 else None
    )

    df_c['Total Score'] = pd.to_numeric(df_c['Total Score'], errors='coerce')

    # Sort and filter data for each figure
    df_sorted = df_c.sort_values(by='Total Score', ascending=False).head(20)
        # Create the bar chart
    bar_chart1 = px.bar(
        df_sorted,
        x='Trip',
        y='Total Score',
        color = 'Total Score',
        color_discrete_sequence=px.colors.qualitative.Bold  # Use the 'bold' color palette
    )

    # Add values to each bar
    bar_chart1.update_traces(
        text=round(df_sorted['Total Score'],3),
        textposition='outside'
    )

            # Adjust the layout to remove the color scale and set font sizes
    bar_chart1.update_layout(
        font=dict(size=24),  # Set global font size
        yaxis=dict(
            range=[0, df_sorted['Total Score'].max() + 1],
            title=dict(text="Total Score", font=dict(size=22)),  # Y-axis title font size
            tickfont=dict(size=18),  # Y-axis tick font size
            tick0=0,  # Starting tick value
            dtick=0.5,
        ),
        xaxis=dict(
            title=dict(text="Trip", font=dict(size=22)),  # X-axis title font size
            tickfont=dict(size=18)  # X-axis tick font size
        ),
        title=dict(text="Top 20 Trips by Total Score", font=dict(size=32)),  # Chart title font size
        coloraxis_showscale=False,  # Disable the color scale
        showlegend=False,  # Hide the legend
        width=1200,  # Set chart width
        height=800,  # Set chart height
        plot_bgcolor="rgba(0,0,0,0)",  # Transparent plot background
        paper_bgcolor="rgba(0,0,0,0)", # Transparent overall chart background
        hoverlabel=dict(font=dict(size=20 ))
    )

    df_grouped = df_c.groupby('Season')['Trip'].count().reset_index()
    df_grouped.columns = ['Season', 'Count']
    pie_chart1 = px.pie(
        df_grouped, names='Season', values='Count', title='Travelled Season',
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
    pie_chart1.update_traces(
        textfont=dict(size=24)
    )

    area_df = df_c['Area'].value_counts().reset_index()
    area_df.columns = ['Area', 'Count']
    pie_chart2 = px.pie(
        area_df, names='Area', values='Count', title='Trips by Area',
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
    pie_chart2.update_traces(
        textfont=dict(size=24)
    )

    df_length = df_c.sort_values(by='Trail Length', ascending=False).head(20)
    bar_chart2 = px.bar(
        df_length,
        x='Trip',
        y='Trail Length',
        color='Trail Length',
        color_continuous_scale=px.colors.sequential.Electric
    )
    bar_chart2.update_traces(
        text=round(df_length['Trail Length'], 3),
        textposition='outside'
    )
    bar_chart2.update_layout(
        font=dict(size=24),
        yaxis=dict(
            range=[0, df_length['Trail Length'].max() + 1],
            title=dict(text="Trail Length", font=dict(size=22)),
            tickfont=dict(size=18),
            tick0=0,
            dtick=1
        ),
        xaxis=dict(
            title=dict(text="Trip", font=dict(size=22)),
            tickfont=dict(size=18)
        ),
        title=dict(text="Top 20 Trips by Trail Length", font=dict(size=32)),
        coloraxis_showscale=False,
        showlegend=False,
        width=1200,
        height=800,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font=dict(size=20))
    )

    histogram_plot = create_histogram(df_c)
    scatter_plot = create_scatter_plot(df_c)

    return bar_chart1, pie_chart1, pie_chart2, bar_chart2, histogram_plot, scatter_plot

        
# Define the main layout with tabs
app.layout = html.Div(
    [
        dcc.Tabs(
            [
                dcc.Tab(
                    label='Trips Calculation',
                    children=tab1_layout(),
                    style=tab_style,
                    selected_style=selected_tab_style
                ),
                dcc.Tab(
                    label='Trips Analysis',
                    children=tab2_layout(),
                    style=tab_style,
                    selected_style=selected_tab_style
                ),
                dcc.Tab(
                    label='Trips Filtering',
                    children=tab3_layout(),
                    style=tab_style,
                    selected_style=selected_tab_style
                ),
                dcc.Tab(
                    label='Trips Dashboard',
                    children=tab4_layout(),
                    style=tab_style,
                    selected_style=selected_tab_style
                )
            ]
        )
    ]
)



if __name__ == "__main__":
    app.run_server(host='100.74.93.47', port=8050, debug=True)