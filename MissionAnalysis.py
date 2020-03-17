import orekit
vm = orekit.initVM()


from PropagationTimeSettings import PropagationTimeSettings
from OEMAndJSONConverter import OEMAndJSONConverter
import json
from org.hipparchus.geometry.euclidean.threed import Vector3D
from org.orekit.frames import FramesFactory, TopocentricFrame
from org.orekit.bodies import OneAxisEllipsoid, GeodeticPoint, CelestialBodyFactory
from org.orekit.utils import IERSConventions, Constants
from org.orekit.orbits import KeplerianOrbit, PositionAngle
from org.orekit.utils import PVCoordinates
from org.orekit.propagation.analytical import KeplerianPropagator
from org.orekit.propagation.events.handlers import EventHandler
from org.orekit.propagation.analytical.tle import TLE, TLEPropagator
from org.orekit.python import PythonEventHandler, PythonOrekitFixedStepHandler
from math import radians, pi, degrees


class HAL_MissionAnalysis(PropagationTimeSettings):
    """
    Class that permit to propagate TLE, KEPLERIAN, CARTESIAN Satellite position to RETURN :
    ephemerids (on a JSON format or CCSDS file)
    visibility if ground station has been added
    """

    def __init__(self, timeStep, duration):
        """Constructor specifies the time settings of the propagation """
        #Heritage Method
        PropagationTimeSettings.__init__(self, int(timeStep), int(duration))

        #Needed Constant Init
        self.ae = Constants.WGS84_EARTH_EQUATORIAL_RADIUS
        self.mu = Constants.WGS84_EARTH_MU

        #Parameter Init
        self.inertialFrame = FramesFactory.getEME2000()
        self.satelliteList = {} # Satellite List saved like a KeplerianOrbit, Key of Element is satellite Name
        self.tleList = {}
        self.rawEphemeridsList = {} # epoch, x, y, z, vx, vy, vz data sor by satellite Name
        self.groundStationList = {} # GroundStationList
        self.visibilityMatrice = {}

        #lupinArray is storing ground station pointing informations on an array
        # 1 information is represented by the following json
        # {
        # "station": "cayenne",
        # "date": "2019-12-25T17:15:00Z",
        # "azimuth": 53,
        # "elevation": 18
        #     }
        self.lupinArray = []


    def addSatellite(self, satellite):
        """
        Add 1 satellite to the ones to propagate
        :param satellite:
        :return:
        """

        if(satellite["type"] == "keplerian"):
            try:
                orbit = KeplerianOrbit(float(satellite["sma"]), float(satellite["ecc"]),
                                       radians(float(satellite["inc"])),
                                       radians(float(satellite["pa"])), radians(float(satellite["raan"])),
                                       float(satellite["meanAnomaly"]),
                                       PositionAngle.TRUE, self.inertialFrame, self.absoluteStartTime, self.mu)
                self.satelliteList[satellite["name"]] = {
                    "initialState": orbit,
                    "propagator": KeplerianPropagator(orbit)
                }
            except:
                raise NameError("start time is not defined.")

        elif(satellite["type"] == "cartesian"):
            try:
                position = Vector3D(float(satellite["x"]), float(satellite["y"]), float(satellite["z"]))
                velocity = Vector3D(float(satellite["vx"]), float(satellite["vy"]), float(satellite["vz"]))
                orbit = KeplerianOrbit(PVCoordinates(position, velocity), FramesFactory.getEME2000(),
                                       self.absoluteStartTime, self.mu)
                self.satelliteList[satellite["name"]] = {
                    "initialState": orbit,
                    "propagator": KeplerianPropagator(orbit)
                }
            except:
                raise NameError("start time is not define")

        elif(satellite["type"] == "tle"):
            line1 = satellite["line1"]
            line2 = satellite["line2"]
            tle = TLE(satellite["line1"], satellite["line2"])
            propagator = TLEPropagator.selectExtrapolator(tle)
            self.absoluteStartTime = tle.getDate()
            self.absoluteEndTime = self.absoluteStartTime.shiftedBy(self.duration)
            self.satelliteList[satellite["name"]] = {
                "initialSate": tle,
                "propagator": propagator
            }

    def addGroundStation(self, groundStation):
        """
        Add 1 groundStation to the ones to register
        :param groundStation:
        :return:
        """
        ITRF = FramesFactory.getITRF(IERSConventions.IERS_2010, True)
        station = GeodeticPoint(radians(float(groundStation["latitude"])),radians(float(groundStation["longitude"])), float(groundStation["altitude"]))
        earth = OneAxisEllipsoid(Constants.WGS84_EARTH_EQUATORIAL_RADIUS,
                                 Constants.WGS84_EARTH_FLATTENING,
                                 ITRF)
        stationFrame = TopocentricFrame(earth, station, groundStation["name"])
        self.groundStationList[groundStation["name"]] = { "station": stationFrame, "passing": False,
                                                          "elev": float(groundStation["elevation"]) }

    def getSatelliteList(self):
        """Return Satellite list to propagate"""
        return self.satelliteList

    def getGroundStationList(self):
        """
        Return ground Station list
        :return:
        """
        return self.groundStationList

    def propagate(self):
        """
        Execute the propagation calculation
        """
        #Initialize lupinArray that will store object


        # Initialze python array in dictionary
        for key, value in self.satelliteList.items():
            self.rawEphemeridsList[key] = []

        # Initialize matrice of visibility

        for gsKey, gsValue in self.groundStationList.items():
            self.visibilityMatrice[gsKey] = {}
            for satKey, satValue in self.satelliteList.items():
                self.visibilityMatrice[gsKey][satKey] = []
                # Seront Stocker dans la visibilityMatrice les élements suivants
                # startingDate, endingDate, azimuthBegining, azimuthEnd

        # Propagate
        extrapDate = self.absoluteStartTime
        while (extrapDate.compareTo(self.absoluteEndTime) <= 0.0):
            for satKey, satValue in self.satelliteList.items():
                currState = satValue['propagator'].propagate(extrapDate)

                # Get and Format Ephemerids Informations
                pVCoordinates = currState.getOrbit().getPVCoordinates()
                position = pVCoordinates.getPosition()
                velocity= pVCoordinates.getVelocity()

                # Format and Append position propagate to array
                currData = {
                    "epoch": str(self.absDate2ISOString(currState.getDate())),
                    "x": round(position.getX(), 7),
                    "y": round(position.getY(), 7),
                    "z": round(position.getZ(), 7),
                    "vx": round(velocity.getX(), 7),
                    "vy": round(velocity.getY(), 7),
                    "vz": round(velocity.getZ(), 7)
                }
                self.rawEphemeridsList[satKey].append(currData)

                # Calculate and Format visibility Informations
                for gsKey, gsValue in self.groundStationList.items():
                    el_tmp = degrees(gsValue["station"].getElevation(position, self.inertialFrame, extrapDate))
                    az_tmp = degrees(gsValue["station"].getAzimuth(position, self.inertialFrame, extrapDate))
                    temp_data = {}
                    if el_tmp >= gsValue["elev"]:
                        ## LUPIN CODE
                        # self.lupinArray.append({
                        #     "date": self.absDate2ISOString(currState.getDate()),
                        #     "station": gsKey,
                        #     "elevation": el_tmp,
                        #     "azimuth": az_tmp
                        # })

                        ## FIN LUPIN CODE
                        if not self.visibilityMatrice[gsKey][satKey] or self.visibilityMatrice[gsKey][satKey][
                                -1]["passing"] == False:
                            temp_data['startDate'] = str(self.absDate2datetime(currState.getDate()))
                            temp_data['startAz'] = az_tmp
                            temp_data['passing'] = True
                            self.visibilityMatrice[gsKey][satKey].append(temp_data)
                    else:
                        ## Si le tableau a dejà commencé à être rempli et que la matrice de visibilitié
                        if  len(self.visibilityMatrice[gsKey][satKey])>0 and self.visibilityMatrice[gsKey][satKey][-1]["passing"] == True:
                            self.visibilityMatrice[gsKey][satKey][-1]["endDate"] = str(self.absDate2datetime(currState.getDate()))
                            self.visibilityMatrice[gsKey][satKey][-1]["endAz"] = az_tmp
                            self.visibilityMatrice[gsKey][satKey][-1]["passing"] = False


            extrapDate = extrapDate.shiftedBy(self.timeStep)
        # Format data Ephemeris data
        self.formatedData = OEMAndJSONConverter(self.rawEphemeridsList)



    def getJSONEphemerids(self):
        """
        Get Ephemerids in JSON format
        :param outputFormat:
        :return:
        """
        assert (self.formatedData is not None)
        return self.formatedData.getJSON()

    def _getRawData(self):
        """
        Get Ephemerids data in a weirdo format
        :return:
        """
        assert (self.rawEphemeridsList is not None)
        return self.rawEphemeridsList

    def getOEMEphemerids(self):
        """
        Get Ephemerids in OEM format
        :param outputFormat:
        :return:
        """
        assert (self.formatedData is not None)
        return self.formatedData.getOEM()

    def getVisibility(self):
        """
        return Visibiity to the asked format
        :return:
        """
        assert (self.visibilityMatrice is not None)
        return self.visibilityMatrice

    def saveJsonFile(self, data, jsonFileName):
        """
        Save a dictionary into a json file
        :param dictTionary:
        :param jsonFile:
        :return:
        """
        with open(jsonFileName + '.json', 'w') as fp:
            json.dump(data, fp, sort_keys=True, indent=4)

if __name__ == "__main__":
    import time
    from pprint import pprint
    # Init orekit

    mySatelliteKeplerian = {
        "name": "Lucien-Sat",
        "type": "keplerian",
        "sma": 7000000,
        "ecc": 0.007014455530245822,
        "inc": 51,
        "pa": 0,
        "raan": 0,
        "meanAnomaly": 0,
    }

    mySatelliteCartesian = {
        "name": "Thibault-Sat",
        "type": "cartesian",
        "x": -6142438.668,
        "y": 3492467.560,
        "z": -25767.25680,
        "vx": 505.8479685,
        "vy": 942.7809215,
        "vz": 7435.922231,
    }

    mySatelliteTLE = {
        "name": "ISS (ZARYA)",
        "type": "tle",
        "line1": "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927",
        "line2": "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"
    }

    isae = {
        "name": "ISAE-SUPAERO",
        "latitude": 43,
        "longitude": 1.5,
        "altitude": 150,
        "elevation": 12
    }
    #
    # cayenne = {
    #     "name": "cayenne",
    #     "latitude": 4.5,
    #     "longitude": -52.9,
    #     "altitude": 0,
    #     "elevation": 12
    # }

    # mySuperStation2 = {
    #     "name": "TERRA-INCONITA",
    #     "latitude": 44,
    #     "longitude": 22,
    #     "altitude": 800,
    #     "elevation": 9
    # }

    start = time.time()

    #Init time of the mission analysis ( initial date, step between propagation, and duration)
    myPropagation = HAL_MissionAnalysis(1, 6000)
    myPropagation.setStartingDate("2019-02-22T18:30:00Z")

    #Add my ground station
    myPropagation.addGroundStation(isae)
    #myPropagation.addGroundStation(cayenne)

    #Add Satellites
    # myPropagation.addSatellite(mySatelliteTLE)
    myPropagation.addSatellite(mySatelliteCartesian)
    myPropagation.addSatellite(mySatelliteKeplerian)

    # Propagate
    myPropagation.propagate()

    end = time.time()

    print("Execution time : "+ str(round(end-start, 3)) )

    #Get Result
    #pprint(myPropagation.lupinArray)
    #myPropagation.saveJsonFile(myPropagation.getJSONEphemerids(), 'data')
    pprint(myPropagation.getJSONEphemerids())
    #print(myPropagation.getOEMEphemerids())
    # pprint(myPropagation.getVisibility())
    #myPropagation.getEclipse()