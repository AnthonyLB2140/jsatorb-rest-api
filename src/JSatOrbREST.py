from distutils.dir_util import copy_tree
import os
import sys
import io
import zipfile
from bottle import HTTPResponse

#### Give visibility on processing modules called from the REST API
# Add mission analysis module 
sys.path.append('../jsatorb-visibility-service/src')
# Add eclipses module 
sys.path.append('../jsatorb-eclipse-service/src')
# Add Date conversion module 
sys.path.append('../jsatorb-date-conversion/src')
# Add JSatOrb common module: AEM and MEM generators
sys.path.append('../jsatorb-common/src')
sys.path.append('../jsatorb-common/src/AEM')
sys.path.append('../jsatorb-common/src/MEM')
sys.path.append('../jsatorb-common/src/VTS')
# Add file conversion module
sys.path.append('../jsatorb-common/src/file-conversion')
# Add JSatOrb common module: Mission Data management
sys.path.append('../jsatorb-common/src/mission-mgmt')

import bottle
from bottle import request, response
from MissionAnalysis import HAL_MissionAnalysis
from DateConversion import HAL_DateConversion
from EclipseCalculator import HAL_SatPos, EclipseCalculator
from FileGenerator import FileGenerator
from VTSGenerator import VTSGenerator
from ccsds2cic import ccsds2cic
from MissionDataManager import writeMissionDataFile, loadMissionDataFile, listMissionDataFile, duplicateMissionDataFile, isMissionDataFileExists, deleteMissionDataFile
from datetime import datetime
import json

app = application = bottle.default_app()

# the decorator
def enable_cors(fn):
    def _enable_cors(*args, **kwargs):
        # set CORS headers
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS, DELETE'
        response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

        if bottle.request.method != 'OPTIONS':
            # actual request; reply with the actual response
            return fn(*args, **kwargs)
    return _enable_cors

def showRequest(req):
    """Display received HTTP request on stdout."""
    print("RECEIVED REQUEST --------------------------------------------------")
    print(req)
    print("END OF RECEIVED REQUEST -------------------------------------------")

def showResponse(res):
    """Display sent HTTP response on stdout."""
    print("SENT RESPONSE (truncated to 1000 char) ----------------------------")
    print(res[0:1000])
    print("END OF SENT RESPONSE ----------------------------------------------")

def boolToRESTStatus(value):
    """Convert a boolean to a REST status value {"SUCCESS, "FAIL"}."""
    if (value == True):
        return "SUCCESS"
    else:
        return "FAIL"

def buildSMDResponse(status, message, data):
    """
    Build a formatted REST response as a dictionary: 
    {"status": <operation status: "SUCCESS" or "FAIL">, "message": <error message if "FAIL" is returned>, "data": <response data>}
    """

    return {"status": status, "message": message, "data": data}

# -----------------------------------------------------------------------------
# MODULE        : jsatorb-visibility-service
# ROUTE         : /propagation/satellites
# METHOD        : POST
# FUNCTIONNALITY: Ephemerids processing 
# -----------------------------------------------------------------------------
@app.route('/propagation/satellites', method=['OPTIONS','POST'])
@enable_cors
def satelliteJSON():
    response.content_type = 'application/json'
    data = request.json
    showRequest(json.dumps(data))

    header = data['header']
    satellites = data['satellites']
    step = header['step']
    duration = header['duration']

    # Assign default value ('EARTH') if celestial body is undefined.
    if 'celestialBody' in header:
        celestialBody=header['celestialBody']
    else:
        celestialBody = 'EARTH'
        
    newMission = HAL_MissionAnalysis(step, duration, celestialBody)    

    if 'timeStart' in header:
        newMission.setStartTime(header['timeStart'])

    for sat in  satellites:
        newMission.addSatellite(sat)

    newMission.propagate()

    res = json.dumps(newMission.getJSONEphemerids())
    showResponse(res)
    return res

# -----------------------------------------------------------------------------
# MODULE        : jsatorb-visibility-service
# ROUTE         : /propagation/visibility
# METHOD        : POST
# FUNCTIONNALITY: Visibility processing
# -----------------------------------------------------------------------------
@app.route('/propagation/visibility', method=['OPTIONS', 'POST'])
@enable_cors
def satelliteOEM():
    response.content_type = 'application/json'
    data = request.json
    showRequest(json.dumps(data))

    header = data['header']
    satellites = data['satellites']
    groundStations = data['groundStations']
    step = header['step']
    duration = header['duration']

    # Assign default value ('EARTH') if celestial body is undefined.
    if 'celestialBody' in header:
        celestialBody=header['celestialBody']
    else:
        celestialBody = 'EARTH'
        
    newMission = HAL_MissionAnalysis(step, duration, celestialBody)    
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

# -----------------------------------------------------------------------------
# MODULE        : jsatorb-eclipse-service
# ROUTE         : /propagation/eclipses
# METHOD        : POST
# FUNCTIONNALITY: Eclipse processing
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# MODULE        : jsatorb-date-conversion
# ROUTE         : /dateconversion
# FUNCTIONNALITY: Date conversion from ISO-8601 to JD and MJD
# -----------------------------------------------------------------------------
@app.route('/dateconversion', method=['OPTIONS', 'POST'])
@enable_cors
def DateConversionREST():
    response.content_type = 'application/json'

    data = request.json
    showRequest(json.dumps(data))

    try:
        header = data['header']
        dateToConvert = header['dateToConvert']
        targetFormat = header['targetFormat']

        newDate = HAL_DateConversion(dateToConvert, targetFormat)

        # Return json with converted date in 'dateConverted'

        result = newDate.getDateTime()
        errorMessage = ''
    except Exception as e:
        result = None
        errorMessage = str(e)

    res = json.dumps(buildSMDResponse(boolToRESTStatus(result!=None), errorMessage, result))
    showResponse(res)
    return res

# -----------------------------------------------------------------------------------------
# VTS ZIP FILE BLOB RESPONSE PROTOTYPE FUNCTIONS
# -----------------------------------------------------------------------------------------
# NEW METHOD
#For the given path, get the List of all files in the directory tree 
def getListOfFiles(dirName):
    # create a list of file and sub directories 
    # names in the given directory 
    listOfFile = os.listdir(dirName)
    allFiles = list()
    # Iterate over all the entries
    for entry in listOfFile:
        # Create full path
        fullPath = os.path.join(dirName, entry)
        # If entry is a directory then get the list of files in this directory 
        if os.path.isdir(fullPath):
            allFiles = allFiles + getListOfFiles(fullPath)
        else:
            allFiles.append(fullPath)
                
    return allFiles

# NEW METHOD
def zipped_vts_response(vts_folder, mission):
    buf = io.BytesIO()
    # Get the list of all files in directory tree at given path
    listOfFiles = getListOfFiles(vts_folder)

    with zipfile.ZipFile(buf, 'w') as zipfh:
        for individualFile in listOfFiles:
            dt = datetime.now()
            timeinfo = (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
            info = zipfile.ZipInfo(individualFile, timeinfo)
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(individualFile, 'rb') as content_file:
                content = content_file.read()
                zipfh.writestr(info, content)
    buf.seek(0)

    filename = 'vts-' + mission + '-content.vz'

    r = HTTPResponse(status=200, body=buf)
    r.set_header('Content-Type', 'application/vnd+cssi.vtsproject+zip')
    r.set_header('Content-Disposition', "attachment; filename='" + filename + "'")
    r.set_header('Access-Control-Allow-Origin', '*')
    print(r)
    return r

# NEW METHOD
'''
@app.route('/propagation/satellites', method=['OPTIONS','POST', 'GET'])
@enable_cors
def satelliteJSON():
  print('Returning VTS ZIP File as Response')
  return zipped_vts_response('/home/olivier/JSatOrb/test/vtscontent')
'''

# -----------------------------------------------------------------------------------------
# END OF VTS ZIP FILE BLOB RESPONSE PROTOTYPE FUNCTIONS
# -----------------------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# MODULE        : jsatorb-file-generation
# ROUTE         : /propagation/eclipses
# METHOD        : POST
# FUNCTIONNALITY: Eclipse processing
# -----------------------------------------------------------------------------
@app.route('/vts', method=['OPTIONS', 'POST'])
@enable_cors
def FileGenerationREST():
    #response.content_type = 'application/json'
    data = request.json
    showRequest(json.dumps(data))

    try:
        header = data['header']
        satellites = data['satellites']
        groundStations = data['groundStations']
        options = data['options']

        if 'celestialBody' not in header: header['celestialBody'] = 'EARTH'
        celestialBody = str( header['celestialBody'] )
        
        step = float( header['step'] )
        startDate = str( header['timeStart'] )
        endDate = str( header['timeEnd'] )

        if 'mission' not in header: header['mission'] = 'default_' + satellites[0]['name']
        projectFolder = 'files/' + header['mission'] + '/'
        dataFolder = projectFolder + 'Data/'
        if not os.path.isdir(projectFolder):
            os.mkdir(projectFolder)
            os.mkdir(dataFolder)
        elif not os.path.isdir(dataFolder):
            os.mkdir(dataFolder)
        copy_tree('files/Models', projectFolder+'Models')

        fileGenerator = FileGenerator(startDate, endDate, step, celestialBody, satellites, groundStations, options)
        fileGenerator.generate(dataFolder)

        nameVtsFile = projectFolder + '/' + header['mission'] + '.vts'
        vtsGenerator = VTSGenerator(nameVtsFile, 'mainModel.vts', '../jsatorb-common/src/VTS/')
        vtsGenerator.generate(header, options, satellites, groundStations)

        result = ""
        errorMessage = 'Files generated'

        # Success response
        res = zipped_vts_response(projectFolder, header['mission'])
        print('Returning compressed VTS data structure as Response')

    except Exception as e:
        result = None
        errorMessage = str(e)

        # Error response
        print('An error occured while producing the compressed VTS data structure !')
        res = json.dumps(buildSMDResponse(boolToRESTStatus(result!=None), errorMessage, result))
        showResponse(res)

    return res

# -----------------------------------------------------------------------------
# MODULE        : jsatorb-common
# ROUTE         : /missiondata/<missionName>
# METHOD        : POST
# FUNCTIONNALITY: Store mission data into a file
# -----------------------------------------------------------------------------
@app.route('/missiondata/<missionName>', method=['OPTIONS', 'POST'])
@enable_cors
def MissionDataStoreREST(missionName):
    response.content_type = 'application/json'
    data = request.json
    showRequest(json.dumps(data))

    result = writeMissionDataFile(data, missionName)

    # Return a JSON formatted response containing the REST operation result: status, message and data.
    res = json.dumps(buildSMDResponse(boolToRESTStatus(result[0]), result[1], ""))
    showResponse(res)
    return res

# -----------------------------------------------------------------------------
# MODULE        : jsatorb-common
# ROUTE         : /missiondata/<missionName>
# METHOD        : GET
# FUNCTIONNALITY: Load mission data previously stored
# -----------------------------------------------------------------------------
@app.route('/missiondata/<missionName>', method=['OPTIONS', 'GET'])
@enable_cors
def MissionDataLoadREST(missionName):
    response.content_type = 'application/json'
    data = request.json
    showRequest(json.dumps(data))

    result = loadMissionDataFile(missionName)

    # Return a JSON formatted response containing the REST operation result: status, message and data.
    res = json.dumps(buildSMDResponse(boolToRESTStatus(not result[0]==None), result[1], result[0]))
    showResponse(res)
    return res

# -----------------------------------------------------------------------------
# MODULE        : jsatorb-common
# ROUTE         : /missiondata/list
# METHOD        : GET
# FUNCTIONNALITY: Get a list of mission data previously stored
# -----------------------------------------------------------------------------
@app.route('/missiondata/list', method=['OPTIONS', 'GET'])
@enable_cors
def MissionDataListREST():
    response.content_type = 'application/json'
    data = request.json
    showRequest(json.dumps(data))

    result = listMissionDataFile()

    # Return a JSON formatted response containing the REST operation result: status, message and data.
    res = json.dumps(buildSMDResponse("SUCCESS", "List of available mission data sets", result))
    showResponse(res)
    return res

# -----------------------------------------------------------------------------
# MODULE        : jsatorb-common
# ROUTE         : /missiondata/duplicate
# METHOD        : POST
# FUNCTIONNALITY: Duplicate mission data to another mission file
# -----------------------------------------------------------------------------
@app.route('/missiondata/duplicate', method=['OPTIONS', 'POST'])
@enable_cors
def MissionDataDuplicateREST():
    response.content_type = 'application/json'
    data = request.json
    showRequest(json.dumps(data))

    header = data['header']
    srcMissionName = header['srcMission']
    destMissionName = header['destMission']

    result = duplicateMissionDataFile(srcMissionName, destMissionName)

    # Return a JSON formatted response containing the REST operation result: status, message and data.
    res = json.dumps(buildSMDResponse(boolToRESTStatus(result[0]), result[1], ""))
    showResponse(res)
    return res

# -----------------------------------------------------------------------------
# MODULE        : jsatorb-common
# ROUTE         : /missiondata/check/<missionName>
# METHOD        : GET
# FUNCTIONNALITY: Check if a mission data file exists
# -----------------------------------------------------------------------------
@app.route('/missiondata/check/<missionName>', method=['OPTIONS', 'GET'])
@enable_cors
def CheckMissionDataREST(missionName):
    response.content_type = 'application/json'
    data = request.json
    showRequest(json.dumps(data))

    result = isMissionDataFileExists(missionName)

    # Return a JSON formatted response containing the REST operation result: status, message and data.
    res = json.dumps(buildSMDResponse("SUCCESS", "Check if a mission data set exists", result))
    showResponse(res)
    return res

# -----------------------------------------------------------------------------
# MODULE        : jsatorb-common
# ROUTE         : /missiondata/<missionName>
# METHOD        : DELETE
# FUNCTIONNALITY: Delete a mission data file
# -----------------------------------------------------------------------------
@app.route('/missiondata/<missionName>', method=['OPTIONS', 'DELETE'])
@enable_cors
def DeleteMissionDataREST(missionName):
    response.content_type = 'application/json'
    data = request.json
    showRequest(json.dumps(data))

    result = deleteMissionDataFile(missionName)

    # Return a JSON formatted response containing the REST operation result: status, message and data.
    res = json.dumps(buildSMDResponse(boolToRESTStatus(result[0]), result[1], ""))
    showResponse(res)
    return res


if __name__ == '__main__':
    bottle.run(host = '127.0.0.1', port = 8000)
