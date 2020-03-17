# Mission Analysis v0.01

This code use orekit to make satellites propagation and visibility calculations related to ground stations.

## Prerequisites
- Python3
- Orekit, hyparchus and bottle must be installed

## Launch the service
```
python MissionAnalysisREST.py
```
By default the service is going to run on the **port 8000**

## Propagation Request Example
Route : /propagation/eclipses', POST method
```json
{
  "header": {
    "timeStart": "2011-12-01T16:43:45",
    "step": 60,
    "duration": 86400
  },
  "satellites" : [
    {
      "name": "Lucien-Sat",
      "type": "keplerian",
      "sma": "7128137.0",
      "ecc": "0.007014455530245822",
      "inc": "98.55",
      "pa": "90.0",
      "raan": "5.191699999999999",
      "meanAnomaly": "359.93"
    },
    {
      "name": "Thibault-Sat",
      "type": "cartesian",
      "x": "-6142438.668",
      "y": "3492467.560",
      "z": "-25767.25680",
      "vx": "505.8479685",
      "vy": "942.7809215",
      "vz": "7435.922231"
    },
    {
      "name": "ISS (ZARYA)",
      "type": "tle",
      "line1": "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927",
      "line2": "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"
    }
  ]
}

```

## Visibility Request example
Route : /propagation/visibility', POST method
```json
{
  "header": {
    "timeStart": "2011-12-01T16:43:45",
    "step": 60,
    "duration": 86400
  },
  "groundStations":[
  	{	
  		"name": "ISAE-SUPAERO",
        "latitude": "22",
        "longitude": "40",
        "altitude": "150",
        "elevation": "12"
    },
    {
        "name": "TERRA-INCONITA",
        "latitude": "44",
        "longitude": "22",
        "altitude": "800",
        "elevation": "9"
    }],
  "satellites" : [
        {
      "name": "Lucien-Sat",
      "type": "keplerian",
      "sma": "7128137.0",
      "ecc": "0.007014455530245822",
      "inc": "98.55",
      "pa": "90.0",
      "raan": "5.191699999999999",
      "meanAnomaly": "359.93"
    },
    {
      "name": "Thibault-Sat",
      "type": "cartesian",
      "x": "-6142438.668",
      "y": "3492467.560",
      "z": "-25767.25680",
      "vx": "505.8479685",
      "vy": "942.7809215",
      "vz": "7435.922231"
    },
    {
      "name": "ISS (ZARYA)",
      "type": "tle",
      "line1": "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927",
      "line2": "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"
    }
  ]
}
```