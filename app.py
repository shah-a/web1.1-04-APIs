# Bismillah al-Rahmaan al-Raheem
# Ali Shah | Dec. 02, 2020
# WEB1.1 Assignment 4: APIs

import os
import requests

from pprint import PrettyPrinter
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from flask import Flask, render_template, request, send_file

from io import BytesIO
import matplotlib.pyplot as plot

################################################################################
## SETUP
################################################################################

app = Flask(__name__)

# Get the API key from the '.env' file
load_dotenv()
API_KEY = os.getenv('API_KEY')

pp = PrettyPrinter(indent=2)

################################################################################
## ROUTES
################################################################################

@app.route('/')
def home():
    """Displays the homepage with forms for current or historical data."""
    context = {
        'min_date': (datetime.now() - timedelta(days=5)),
        'max_date': datetime.now()
    }
    return render_template('home.html', **context)

def get_units_for_temp(units):
    """Returns a shorthand letter for the given units."""
    return 'F' if units == 'imperial' else 'C' if units == 'metric' else 'K'

def get_units_for_wind(units):
    """Returns appropriate units for wind speed."""
    return 'm/s' if units in ('metric', 'kelvin') else 'mph'

@app.route('/results')
def results():
    """Displays results for current weather conditions."""

    city = request.args.get('city')
    units = request.args.get('units')

    # API docs: https://openweathermap.org/current
    URL = 'http://api.openweathermap.org/data/2.5/weather'
    params = {
        'appid': API_KEY,
        'q': city,
        'units': units
    }

    result_json = requests.get(URL, params=params).json()

    # Uncomment the line below to see the results of the API call!
    # pp.pprint(result_json)

    try:
        t_zone = timezone(timedelta(hours=result_json['timezone']/3600))
        context = {
            'date': datetime.now(tz=t_zone),
            'city': f"{result_json['name']}, {result_json['sys']['country']}",
            'description': result_json['weather'][0]['description'],
            'temp': result_json['main']['temp'],
            'humidity': result_json['main']['humidity'],
            'wind_speed': result_json['wind']['speed'],
            'sunrise': datetime.fromtimestamp(result_json['sys']['sunrise'], tz=t_zone),
            'sunset': datetime.fromtimestamp(result_json['sys']['sunset'], tz=t_zone),
            'temp_units': get_units_for_temp(units),
            'wind_units': get_units_for_wind(units)
        }
    except:
        return render_template('error.html', city=city)

    return render_template('results.html', **context)

def get_min_temp(hourly_results):
    """Returns the minimum temp for the given hourly weather objects."""
    temps = [result['temp'] for result in hourly_results]
    return min(temps)

def get_max_temp(hourly_results):
    """Returns the maximum temp for the given hourly weather objects."""
    temps = [result['temp'] for result in hourly_results]
    return max(temps)

def get_lat_lon(city_name):
    """Get latitude and longitude."""
    geolocator = Nominatim(user_agent='Weather Application')
    location = geolocator.geocode(city_name)
    if location is not None:
        return location.latitude, location.longitude
    return 0, 0


@app.route('/historical_results')
def historical_results():
    """Displays historical weather forecast for a given day."""

    city = request.args.get('city')
    date = request.args.get('date') + " +0000"
    units = request.args.get('units')
    date_obj = datetime.strptime(date, '%Y-%m-%d %z')
    date_in_seconds = date_obj.timestamp()
    latitude, longitude = get_lat_lon(city)

    # API docs: https://openweathermap.org/api/one-call-api
    URL = 'http://api.openweathermap.org/data/2.5/onecall/timemachine'
    params = {
        'appid': API_KEY,
        'lat': latitude,
        'lon': longitude,
        'units': units,
        'dt': int(date_in_seconds)
    }

    result_json = requests.get(URL, params=params).json()

    # Uncomment the line below to see the results of the API call!
    # pp.pprint(result_json)

    current_results = result_json['current']
    hourly_results = result_json['hourly']

    context = {
        'city': city,
        'date': date_obj,
        'lat': latitude,
        'lon': longitude,
        'units': units,
        'temp_units': get_units_for_temp(units),
        'description': current_results['weather'][0]['description'],
        'temp': current_results['temp'],
        'min_temp': get_min_temp(hourly_results),
        'max_temp': get_max_temp(hourly_results)
    }

    if result_json['lat'] == 0 and result_json['lon'] == 0:
        return render_template('error.html', city=city)

    return render_template('historical_results.html', **context)

################################################################################
## GRAPH IMAGE
################################################################################

def make_graph_image(x_data, y_data, x_label, y_label):
    """
    Creates and returns a line graph with the given data.
    Written with help from http://dataviztalk.blogspot.com/2016/01/serving-matplotlib-plot-that-follows.html
    """
    plot.switch_backend('Agg')  # Reference: https://github.com/matplotlib/matplotlib/issues/14304/#issuecomment-545717061
    fig, _ = plot.subplots()
    plot.plot(x_data, y_data)
    plot.xlabel(x_label)
    plot.ylabel(y_label)
    img = BytesIO()
    fig.savefig(img)
    img.seek(0)
    return send_file(img, mimetype='image/png')

@app.route('/graph/<lat>/<lon>/<units>/<date>')
def graph(lat, lon, units, date):
    """
    Returns a line graph with data for the given location & date.
    @param lat The latitude.
    @param lon The longitude.
    @param units The units (imperial, metric, or kelvin)
    @param date The date, in the format %Y-%m-%d.
    """

    date_obj = datetime.strptime(date, '%Y-%m-%d')
    date_in_seconds = date_obj.timestamp()

    # API docs: https://openweathermap.org/api/one-call-api
    URL = 'http://api.openweathermap.org/data/2.5/onecall/timemachine'
    params = {
        'appid': API_KEY,
        'lat': lat,
        'lon': lon,
        'units': units,
        'dt': int(date_in_seconds)
    }

    result_json = requests.get(URL, params=params).json()

    # Uncomment the line below to see the results of the API call!
    # pp.pprint(result_json)

    temps = [result['temp'] for result in result_json['hourly']]
    hours = range(len(temps))
    image = make_graph_image(
        hours,
        temps,
        'Hour (UTC)',
        f'Temperature ({get_units_for_temp(units)})'
    )
    return image

if __name__ == '__main__':
    app.run(debug=True)
