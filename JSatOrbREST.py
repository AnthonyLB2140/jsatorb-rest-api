# Give visibility on processing modules called from the REST API
import sys
# Add mission analysis module 
sys.path.append('../jsatorb-visibility-service')
# Add Date conversion module 
sys.path.append('../jsatorb-date-conversion')

import bottle
from bottle import request, response
from MissionAnalysis import HAL_MissionAnalysis
from DateConversion import HAL_DateConversion
import json

app = application = bottle.default_app()

# the decorator
def enable_cors(fn):
    def _enable_cors(*args, **kwargs):
        # set CORS headers
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

        if bottle.request.method != 'OPTIONS':
            # actual request; reply with the actual response
            return fn(*args, **kwargs)
    return _enable_cors

# --------------------------------------------------------------
# MODULE        : jsatorb-visibility-service
# ROUTE         : /propagation/satellites
# FUNCTIONNALITY: Ephemerids processing 
# --------------------------------------------------------------
@app.route('/propagation/satellites', method=['OPTIONS','POST'])
@enable_cors
def satelliteJSON():
    response.content_type = 'application/json'
    data = request.json
    print(json.dumps(data))
    header = data['header']
    satellites = data['satellites']
    newMission = HAL_MissionAnalysis(header['step'], header['duration'])
    if 'timeStart' in header:
        newMission.setStartTime(header['timeStart'])

    for sat in  satellites:
        newMission.addSatellite(sat)

    newMission.propagate()
    return json.dumps(newMission.getJSONEphemerids())

# --------------------------------------------------------------
# MODULE        : jsatorb-visibility-service
# ROUTE         : /propagation/visibility
# FUNCTIONNALITY: Visibility processing
# --------------------------------------------------------------
@app.route('/propagation/visibility', method=['OPTIONS', 'POST'])
@enable_cors
def satelliteOEM():
    response.content_type = 'application/json'
    data = request.json
    header = data['header']
    satellites = data['satellites']
    groundStations = data['groundStations']
    newMission = HAL_MissionAnalysis(header['step'], header['duration'])
    if 'timeStart' in header:
        newMission.setStartTime(header['timeStart'])

    for sat in  satellites:
        newMission.addSatellite(sat)

    for gs in groundStations:
        newMission.addGroundStation(gs)

    newMission.propagate()
    return json.dumps(newMission.getVisibility())

# --------------------------------------------------------------
# MODULE        : jsatorb-eclipse-service
# ROUTE         : /propagation/eclipses
# FUNCTIONNALITY: Eclipse processing
# --------------------------------------------------------------
# @app.route('/propagation/eclipses', method=['OPTIONS', 'POST'])
# @enable_cors
# def EclipsesREST():
#     response.content_type = 'application/json'
#     data = request.json
#     header = data['header']
#     dateToConvert = header['timeStart']
#     targetFormat = header['duration']
#     sat = data['satellite']

#     newEclipses = HAL_Eclipses(timeStart, duration, sat)

#     # Return json with processed Eclipses data
#     return json.dumps(newEclipses.getEclipsesData())


# --------------------------------------------------------------
# MODULE        : jsatorb-date-conversion
# ROUTE         : /dateconversion
# FUNCTIONNALITY: Date conversion from ISO-8601 to JD and MJD
# --------------------------------------------------------------
@app.route('/dateconversion', method=['OPTIONS', 'POST'])
@enable_cors
def DateConversionREST():
    response.content_type = 'application/json'
    data = request.json
    header = data['header']
    dateToConvert = header['dateToConvert']
    targetFormat = header['targetFormat']

    newDate = HAL_DateConversion(dateToConvert, targetFormat)

    # Return json with converted date in 'dateConverted'
    return json.dumps(newDate.getDateTime())

if __name__ == '__main__':
    bottle.run(host = '127.0.0.1', port = 8000)