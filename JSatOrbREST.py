# Give visibility on processing modules called from the REST API
import sys
# Add mission analysis module 
sys.path.append('../jsatorb-visibility-service')
# Add eclipses module 
sys.path.append('../jsatorb-eclipse-service/src')
# Add Date conversion module 
sys.path.append('../jsatorb-date-conversion')

import bottle
from bottle import request, response
from MissionAnalysis import HAL_MissionAnalysis
from DateConversion import HAL_DateConversion
from EclipseCalculator import HAL_SatPos, EclipseCalculator
from datetime import datetime
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

# Method to output the HTTP Requests
def showRequest(req):
    print("RECEIVED REQUEST --------------------------------------------------")
    print(req)
    print("END OF RECEIVED REQUEST -------------------------------------------")

# Method to output the HTTP Responses
def showResponse(res):
    print("SENT RESPONSE (truncated to 1000 char) ----------------------------")
    print(res[0:1000])
    print("END OF SENT RESPONSE ----------------------------------------------")


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
    showRequest(json.dumps(data))

    header = data['header']
    satellites = data['satellites']
    newMission = HAL_MissionAnalysis(header['step'], header['duration'])
    if 'timeStart' in header:
        newMission.setStartTime(header['timeStart'])

    for sat in  satellites:
        newMission.addSatellite(sat)

    newMission.propagate()

    res = json.dumps(newMission.getJSONEphemerids())
    showResponse(res)
    return res


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
    showRequest(json.dumps(data))

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

    res = json.dumps(newMission.getVisibility())
    showResponse(res)
    return res


# --------------------------------------------------------------
# MODULE        : jsatorb-eclipse-service
# ROUTE         : /propagation/eclipses
# FUNCTIONNALITY: Eclipse processing
# --------------------------------------------------------------
@app.route('/propagation/eclipses', method=['OPTIONS','POST'])
@enable_cors
def EclipseCalculatorREST():
    response.content_type = 'application/json'
    
    data = request.json
    showRequest(json.dumps(data))
    
    stringDateFormat = '%Y-%m-%dT%H:%M:%S'

    try:
        header = data['header']
        sat = data['satellite']

        stringDate = str( header['timeStart'] )
        duration = float( header['duration'] )

        typeSat = str( sat['type'] )
        if 'keplerian' in typeSat:
            sma = float( sat['sma'] )
            if sma < 6371000:
                res = ValueError('bad sma value')
            else:
                ecc = float( sat['ecc'] )
                inc = float( sat['inc'] )
                pa = float( sat['pa'] )
                raan = float( sat['raan'] )
                lv = float( sat['meanAnomaly'] )
                calculator = EclipseCalculator(HAL_SatPos(sma, ecc, inc, pa, raan, lv, 'keplerian'),
                    datetime.strptime(stringDate, stringDateFormat), duration)
                res = eclipseToJSON( calculator.getEclipse() )

        elif 'cartesian' in typeSat:
            x = float( sat['x'] )
            y = float( sat['y'] )
            z = float( sat['z'] )
            vx = float( sat['vx'] )
            vy = float( sat['vy'] )
            vz = float( sat['vz'] )
            calculator = EclipseCalculator(HAL_SatPos(x, y, z, vx, vy, vz, 'cartesian'), 
                datetime.strptime(stringDateFormat, stringDateFormat), duration)
            res = eclipseToJSON( calculator.getEclipse() )

        else:
            res = error('bad type')

    except Exception as e:
        res = error(type(e).__name__)

    showResponse(res)
    return res


def error(errorName):
    return '{"error": "' + errorName + '"}'

def eclipseToJSON(eclipse):
    eclipseDictionary = []

    for el in eclipse:
        obj = {}
        obj['start'] = el[0].toString()
        obj['end'] = el[1].toString()
        eclipseDictionary.append(obj)

    return json.dumps(eclipseDictionary)


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
    showRequest(json.dumps(data))

    header = data['header']
    dateToConvert = header['dateToConvert']
    targetFormat = header['targetFormat']

    newDate = HAL_DateConversion(dateToConvert, targetFormat)

    # Return json with converted date in 'dateConverted'
    res = json.dumps(newDate.getDateTime())
    showResponse(res)
    return res


if __name__ == '__main__':
    bottle.run(host = '127.0.0.1', port = 8000)