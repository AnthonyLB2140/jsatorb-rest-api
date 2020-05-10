# List of Attitudes
This is a list of standard attitudes that can be used.

## LOF (Local Orbital Frame)
LOFType.valueOf(String name), LofOffset(Frame inertialFrame, LOFType type)
### LVLH
Constant for Local Vertical, Local Horizontal frame (X axis aligned with position, Z axis aligned with orbital momentum).
### QSW
Constant for QSW frame (X axis aligned with position, Z axis aligned with orbital momentum).
### TNW
Constant for TNW frame (X axis aligned with velocity, Z axis aligned with orbital momentum).
### VNC
Constant for Velocity - Normal - Co-normal frame (X axis aligned with velocity, Y axis aligned with orbital momentum).
### VVLH
Constant for Vehicle Velocity, Local Horizontal frame (Z axis aligned with opposite of position, Y axis aligned with opposite of orbital momentum).

## Body center Pointing
BodyCenterPointing(Frame inertialFrame, Ellipsoid shape)

## Nadir Pointing
NadirPointing(Frame inertialFrame, BodyShape shape)
