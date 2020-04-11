# Give visibility on processing modules called from the REST API
import sys
# Add mission analysis module 
sys.path.append('../jsatorb-visibility-service/src')
# Add eclipses module 
sys.path.append('../jsatorb-eclipse-service/src')
# Add Date conversion module 
sys.path.append('../jsatorb-date-conversion/src')
# Add JSatOrb common module: AEM and MEM generators
sys.path.append('../jsatorb-common/AEM')
sys.path.append('../jsatorb-common/MEM')
# Add JSatOrb common module: file conversion
sys.path.append('../jsatorb-common/file-conversion')
# Add JSatOrb common module: Mission Data management
sys.path.append('../jsatorb-common/src/mission-mgmt')

import bottle
from bottle import request, response
from MissionAnalysis import HAL_MissionAnalysis
from DateConversion import HAL_DateConversion
from EclipseCalculator import HAL_SatPos, EclipseCalculator
from AEMGenerator import AEMGenerator
from MEMGenerator import MEMGenerator
from ccsds2cic import ccsds2cic
from MissionDataManager import writeMissionDataFile, loadMissionDataFile, listMissionDataFile
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
                datetime.strptime(stringDate, stringDateFormat), duration)
            res = eclipseToJSON( calculator.getEclipse() )

        else:
            res = error('bad type')

    except Exception as e:
        res = error(type(e).__name__ + str(e.args))

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

# --------------------------------------------------------------
# MODULE        : jsatorb-file-generation
# ROUTE         : /propagation/eclipses
# FUNCTIONNALITY: Eclipse processing
# --------------------------------------------------------------
@app.route('/vts', method=['OPTIONS','POST'])
@enable_cors
def FileGenerationREST():
    response.content_type = 'application/json'
    data = request.json
    showRequest(json.dumps(data))

    header = data['header']
    satellites = data['satellites']
    groundStations = data['groundStations']
    options = data['options']

    step = float( header['step'] )
    duration = float( header['duration'] )
    stringDate = str( header['timeStart'] )

    fileFolder = 'files/'
    # One file minimum per satellite
    for sat in satellites:
        # OEM
        nameFileOemCcsds = fileFolder + sat['name'] + '.OEM_ccsds'
        nameFileOem = fileFolder + sat['name'] + '.OEM'

        newMission = HAL_MissionAnalysis(step, duration)
        newMission.setStartTime(stringDate)
        newMission.addSatellite(sat)
        newMission.propagate()
        with open(nameFileOemCcsds,'w') as file:
            file.write(newMission.getOEMEphemerids())
        ccsds2cic(nameFileOemCcsds, nameFileOem)

        # AEM
        if 'ATTITUDE' in options:
            nameFileAemCcsds = fileFolder + sat['name'] + '.AEM_ccsds'
            nameFileAem = fileFolder + sat['name'] + '.AEM'

            aemGenerator = AEMGenerator(stringDate, step, duration)
            aemGenerator.setSatellite(sat)
            aemGenerator.setFile(nameFileAemCcsds)
            aemGenerator.setAttitudeLaw('')
            aemGenerator.propagate()
            ccsds2cic(nameFileAemCcsds, nameFileAem)

            options.remove('ATTITUDE')

        # MEM
        memGenerator = MEMGenerator(stringDate, step, duration)
        memGenerator.setSatellite(sat)
        for memType in options:
            if memType == 'VISIBILITY':
                for gs in groundStations:
                    memGenerator.addMemVisibility(fileFolder + sat['name'] + '_' + memType + '_' + gs['name'] + '.MEM', gs)
            else:
                memGenerator.addMemType(memType, fileFolder + sat['name'] + '_' + memType + '.MEM')

        memGenerator.propagate()

    res = json.dumps({"result": "success"})
    showResponse(res)
    return res

# --------------------------------------------------------------
# MODULE        : jsatorb-common
# ROUTE         : /data/store
# FUNCTIONNALITY: Store mission data into a file
# --------------------------------------------------------------
@app.route('/data/store', method=['OPTIONS', 'POST'])
@enable_cors
def MissionDataStoreREST():
    response.content_type = 'application/json'
    data = request.json
    showRequest(json.dumps(data))

    header = data['header']
    missionName = header['mission']

    status = writeMissionDataFile(data, missionName)

    # Return json containing the writing status
    res = json.dumps(status)
    showResponse(res)
    return res

# --------------------------------------------------------------
# MODULE        : jsatorb-common
# ROUTE         : /data/load
# FUNCTIONNALITY: Load mission data previously stored
# --------------------------------------------------------------
@app.route('/data/load', method=['OPTIONS', 'POST'])
@enable_cors
def MissionDataLoadREST():
    response.content_type = 'application/json'
    data = request.json
    showRequest(json.dumps(data))

    header = data['header']
    missionName = header['mission']

    missionData = loadMissionDataFile(missionName)

    # Return json containing the mission data
    res = json.dumps(missionData)
    showResponse(res)
    return res

# --------------------------------------------------------------
# MODULE        : jsatorb-common
# ROUTE         : /data/list
# FUNCTIONNALITY: Get a list of mission data previously stored
# --------------------------------------------------------------
@app.route('/data/list', method=['OPTIONS', 'POST'])
@enable_cors
def MissionDataListREST():
    response.content_type = 'application/json'
    data = request.json
    showRequest(json.dumps(data))

    listMD = listMissionDataFile()

    # Return json containing the list of available mission data sets
    res = json.dumps(listMD)
    showResponse(res)
    return res


if __name__ == '__main__':
    bottle.run(host = '127.0.0.1', port = 8000)
