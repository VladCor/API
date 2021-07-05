import requests
import flask
from flask import request
from datetime import datetime, timedelta
import sqlite3

APP = flask.Flask(__name__)

# Flights
parametres = {
    "withLeg": "false",
    "withCancelled": "false",
    "withCodeshared": "false",
    "withCargo": "true",
    "withPrivate": "true"
}

nowTime = (datetime.now()).strftime("%Y-%m-%dT%H:%M")
nowPlusTwelfe = (datetime.now() + timedelta(hours=12)
                 ).strftime("%Y-%m-%dT%H:%M")

flightsEndpoint = f"https://aerodatabox.p.rapidapi.com/flights/airports/icao/LRIA/{nowTime}/{nowPlusTwelfe}"
response = requests.get(flightsEndpoint, headers={
    'x-rapidapi-key': "73f511da57msh002eee652e8817ep1ba101jsn7d93fb81f914",
    'x-rapidapi-host': "aerodatabox.p.rapidapi.com"
}, params=parametres)
responseJSON = response.json()
departures = responseJSON['departures']

# Weather
weatherEndpoint = f"https://api.openweathermap.org/data/2.5/onecall?lat=47.1771449&lon=27.6173117&lang=ro&exclude=current,minutely,daily,alerts&units=metric&appid=7f78d9ef3b1c8d32fcc0cfd8deb2459a"
response = requests.get(weatherEndpoint)
responseJSON = response.json()
hourlyWeather = responseJSON['hourly']

# Add weahter data in departures
for departure in departures:
    for hourWeather in hourlyWeather:
        weather_date = datetime.fromtimestamp(hourWeather['dt'])
        departure_date = datetime.fromisoformat(
            departure['movement']['scheduledTimeLocal'])

        formated_weather_date = str(weather_date)[:13]
        formated_departure_date = str(departure_date)[:13]

        if (formated_weather_date == formated_departure_date):
            departure['weatherData'] = hourWeather

# API
@APP.route('/add_condition', methods=['POST'])
def add_condition():
    field = request.form['field']
    condition = request.form['condition']
    value = request.form['value']

    conn = sqlite3.connect('Database.db')
    c = conn.cursor()
    c.execute('insert into conditions values (?,?,?,?)',
              [None, field, condition, value])
    conn.commit()
    conn.close()
    return f"Condition added successfully", 201


def get_conditions():
    conn = sqlite3.connect('Database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM conditions")
    conditionsFromDB = c.fetchall()
    conn.close()
    return conditionsFromDB


@APP.route('/delete_condition/<id>', methods=['POST'])
def delete_condition(id):
    conn = sqlite3.connect('Database.db')
    c = conn.cursor()

    if (id == 'all'):
        c.execute("DELETE FROM conditions")
    else:
        c.execute("DELETE FROM conditions WHERE id = ?", [id])
    conn.commit()
    conn.close()
    return f"Condition deleted successfully", 201


@APP.route('/edit_condition/<id>', methods=['POST'])
def edit_condition(id):
    newValue = request.form['newValue']
    conn = sqlite3.connect('Database.db')
    c = conn.cursor()
    c.execute("UPDATE conditions SET value= ? WHERE id = ?", [newValue, id])
    conn.commit()
    conn.close()
    return f"Condition edited successfully", 201

# Check condition
def check_condition(departure, condition):
    field = condition[1]
    operation = condition[2]
    value = condition[3]

    if (field == 'temp'):
        if (operation == 'sm'):
            return float(departure["weatherData"]["temp"]) < float(value)
        elif (operation == 'eq'):
            return float(departure["weatherData"]["temp"]) == float(value)
        elif (operation == 'gr'):
            return float(departure["weatherData"]["temp"]) > float(value)
    elif (field == 'speed'):
        if (operation == 'sm'):
            return float(departure["weatherData"]["wind_speed"]) < float(value)
        elif (operation == 'eq'):
            return float(departure["weatherData"]["wind_speed"]) == float(value)
        elif(operation == 'gr'):
            return float(departure["weatherData"]["wind_speed"]) > float(value)
    elif (field == 'visibility'):
        if (operation == 'sm'):
            return float(departure["weatherData"]["visibility"]) < float(value)
        elif (operation == 'eq'):
            return float(departure["weatherData"]["visibility"]) == float(value)
        elif(operation == 'gr'):
            return float(departure["weatherData"]["visibility"]) > float(value)
    elif (field == 'weather'):
        if (operation == 'eq'):
            return departure["weatherData"]["weather"][0]["main"] == value


# Pagini
@APP.route('/')
def index():
    # Add recommendation in departures
    cancelConditions = get_conditions()
    for departure in departures:
        isDepartureCanceled = False
        if (cancelConditions):
            for condition in cancelConditions:
                if (check_condition(departure, condition)):
                    departure['recommendation'] = 'Cancel'
                    isDepartureCanceled = True
                else:
                    if (isDepartureCanceled == False):
                        departure['recommendation'] = 'Can fly'
        else:
            departure['recommendation'] = 'Can fly'
    return flask.render_template('index.html', len=len(departures), departures=departures)


@APP.route('/conditions')
def conditions():
    dbConditions = get_conditions()
    return flask.render_template('conditions.html', len=len(dbConditions), dbConditions=dbConditions)


if __name__ == '__main__':
    APP.debug = True
    APP.run()