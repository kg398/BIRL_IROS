#!/usr/bin/env python
# Scripts for iros challenge 3: stir a mug of water with a spoon

import time
import copy
import math

import cv2
import imutils
from matplotlib import pyplot as plt

import iros_interface_cmds as ic
import iros_waypoints as iw
#import vision_copy as vc

## Way points
ee_home = {"act": 80, "servo": 80, "tilt": 30, "vac": "r"}
home = {"x": 90.0, "y": -500.0, "z": 100.0, "rx": 0.0, "ry": 180.0, "rz": 0.0}
home_joints = {"x": 87.61, "y": -87.40, "z": 100.79, "rx": -103.37, "ry": -89.70, "rz": -2.26}

## Object parameters
cup_radius = 25
cup_height = 40
spoon_bowl = 15         # lenght of spoon bowl (to be convered when stirring)
spoon_height = 10
stir_radius = cup_radius - 10
act_spoon = 10

## Location of first mug ()
p_centre = [100, 200]
p_edge = [100, 200]
attack_angle =70

## Loction of second mug
mx_2 = 200
my_2 = 300

#ic.socket_send(c,sCMD=202)
def begin(c,ser_ee):
    # Home for end effector and actuator
    demand_Grip = dict(ee_home)
    demand_Grip["act"] = act_spoon
    msg = ic.safe_move(c,ser_ee,Pose=dict(iw.grab_joints),Grip=demand_Grip,CMD=2)

    # Goto spoon (TO FINISH)
    demand_Pose = dict(home)
    x_p, y_p, ori = get_grasping_coords(p_centre,p_edge)
    angle_grasp(c,ser_ee,x_p,y_p,spoon_height,ori,attack_angle)
    msg = ic.safe_ur_move(c,Pose=demand_Pose,CMD=4)

    # Grasp spoon
    demand_Grip["servo"]=0
    msg = ic.end_effector_move(ser_ee,demand_Grip)

    # Lift spoon
    demand_Pose["z"]=cup_height + 20
    msg = ic.safe_ur_move(c,Pose=demand_Pose,CMD=4)

    ## Move to second cup x, y
    demand_Pose = dict(home)
    demand_Pose["x"]=mx_2
    demand_Pose["y"]=my_2
    msg = ic.safe_ur_move(c,Pose=demand_Pose,CMD=4)

    ## Lower spoon
    demand_Pose["z"]=cup_height-spoon_bowl
    msg = ic.safe_ur_move(c,Pose=demand_Pose,CMD=4)

    ## Stir spoon
    add_stir = [0, stir_radius, 0, -stir_radius, 0]
    for j in range (0,1):
        for i in range (0,3):
            demand_Pose["x"]=mx_2 + add_stir[i+1]
            demand_Pose["y"]=my_2 + add_stir[i]
            msg = ic.safe_ur_move(c,Pose=demand_Pose,CMD=4)

    ## Lift spoon
    demand_Pose["z"]=cup_height+20
    msg = ic.safe_ur_move(c,Pose=demand_Pose,CMD=4

## Home
    demand_Pose = dict(home)
    demand_Pose["x"]=mx_1
    demand_Pose["y"]=my_1
    msg = ic.safe_ur_move(c,Pose=demand_Pose,CMD=4)



def get_grasping_coords(p_centre,p_edge):
    #aoa = 70
    ori = math.atan2(p_centre[1]-p_edge[1],p_centre[0]-p_edge[0])*180.0/math.pi
    size = math.sqrt(math.pow(p_centre[0]-p_edge[0],2)+math.pow(p_centre[1]-p_edge[1],2))
    print "ori: ",ori
    ori = ori-180
    if ori<-180:
        ori=360+ori
    x = p_edge[0]
    y = p_edge[1]
    return float(x[0]), float(y[0]), ori


def angle_grasp(c,ser_ee,x,y,z,orientation,angle_of_attack=attack_angle):
    # Select tcp_2, for rotations around the grasping point
    ic.socket_send(c,sCMD=103)

    # Break-up rotations into max 90degrees
    thetaz = 0
    if orientation>90:
        orientation=orientation-90
        thetaz=math.pi/2
    elif orientation<-90:
        orientation=orientation+90
        thetaz=-math.pi/2

    # Avoid singularity at +/-45degrees
    if orientation==45:
        orientation = 44
    elif orientation==-45:
        orientation = -44

    # Convert to radians
    angle_of_attack=angle_of_attack*math.pi/180.0
    orientation=orientation*math.pi/180.0
    thetay=135.0*math.pi/180.0

    # Cartesian rotation matrices to match uw.grabbing_joints rotation
    x_rot = np.matrix([[ 1.0, 0.0, 0.0],
             [ 0.0, math.cos(math.pi/2), -math.sin(math.pi/2)],
             [ 0.0, math.sin(math.pi/2), math.cos(math.pi/2)]]) # x_rot[rows][columns]
    y_rot = np.matrix([[ math.cos(thetay), 0.0, -math.sin(thetay)],
             [ 0.0, 1.0, 0.0],
             [ math.sin(thetay), 0.0, math.cos(thetay)]]) # y_rot[rows][columns]
    z_rot = np.matrix([[ math.cos(0.0), -math.sin(0.0), 0.0],
             [ math.sin(0.0), math.cos(0.0), 0.0],
             [ 0.0, 0.0, 1.0]]) # z_rot[rows][columns]

    # Move to grabbing waypoint
    msg = ic.safe_ur_move(c,Pose=dict(uw.grabbing_joints_waypoint),Speed=1.0,CMD=2)

    # Create rotation matrix for current position
    R=z_rot*y_rot*x_rot

    if thetaz!=0:
        # Axis rotation matricies for grasping position, rotate around x-axis by aoa, then z-axis by ori
        x_rot = np.matrix([[ 1.0, 0.0, 0.0],
                 [ 0.0, math.cos(angle_of_attack), -math.sin(angle_of_attack)],
                 [ 0.0, math.sin(angle_of_attack), math.cos(angle_of_attack)]]) # x_rot[rows][columns]
        z_rot = np.matrix([[ math.cos(thetaz), -math.sin(thetaz), 0.0],
                 [ math.sin(thetaz), math.cos(thetaz), 0.0],
                 [ 0.0, 0.0, 1.0]]) # z_rot[rows][columns]

        # Cartesian rotation matrix of desired orientation
        R=z_rot*x_rot*R

        # Cartesian to axis-angle
        theta = math.acos(((R[0, 0] + R[1, 1] + R[2, 2]) - 1.0)/2)
        multi = 1 / (2 * math.sin(theta))
        rx = multi * (R[2, 1] - R[1, 2]) * theta * 180/math.pi
        ry = multi * (R[0, 2] - R[2, 0]) * theta * 180/math.pi
        rz = multi * (R[1, 0] - R[0, 1]) * theta * 180/math.pi
        print rx, ry, rz

        # Rotate around tool centre point defined by tcp_2
        current_Pose = ic.get_ur_position(c,1)
        demand_Pose = {"x":current_Pose[0],"y":current_Pose[1],"z":current_Pose[2],"rx":rx,"ry":ry,"rz":rz}
        msg = ic.safe_ur_move(c,Pose=dict(demand_Pose),CMD=8)

        # Axis rotation matricies for grasping position, rotate around x-axis by aoa, then z-axis by ori
        z_rot = np.matrix([[ math.cos(orientation), -math.sin(orientation), 0.0],
                 [ math.sin(orientation), math.cos(orientation), 0.0],
                 [ 0.0, 0.0, 1.0]]) # z_rot[rows][columns]

        # Cartesian rotation matrix of desired orientation
        R=z_rot*R

        # Cartesian to axis-angle
        theta = math.acos(((R[0, 0] + R[1, 1] + R[2, 2]) - 1.0)/2)
        multi = 1 / (2 * math.sin(theta))
        rx = multi * (R[2, 1] - R[1, 2]) * theta * 180/math.pi
        ry = multi * (R[0, 2] - R[2, 0]) * theta * 180/math.pi
        rz = multi * (R[1, 0] - R[0, 1]) * theta * 180/math.pi
        print rx, ry, rz

        # Rotate around tool centre point defined by tcp_2
        current_Pose = ic.get_ur_position(c,1)
        demand_Pose = {"x":current_Pose[0],"y":current_Pose[1],"z":current_Pose[2],"rx":rx,"ry":ry,"rz":rz}
        msg = ic.safe_ur_move(c,Pose=dict(demand_Pose),CMD=8)
    else:
        # Axis rotation matricies for grasping position, rotate around x-axis by aoa, then z-axis by ori
        x_rot = np.matrix([[ 1.0, 0.0, 0.0],
                 [ 0.0, math.cos(angle_of_attack), -math.sin(angle_of_attack)],
                 [ 0.0, math.sin(angle_of_attack), math.cos(angle_of_attack)]]) # x_rot[rows][columns]
        z_rot = np.matrix([[ math.cos(orientation), -math.sin(orientation), 0.0],
                 [ math.sin(orientation), math.cos(orientation), 0.0],
                 [ 0.0, 0.0, 1.0]]) # z_rot[rows][columns]

        # Cartesian rotation matrix of desired orientation
        R=z_rot*x_rot*R

        # Cartesian to axis-angle
        theta = math.acos(((R[0, 0] + R[1, 1] + R[2, 2]) - 1.0)/2)
        multi = 1 / (2 * math.sin(theta))
        rx = multi * (R[2, 1] - R[1, 2]) * theta * 180/math.pi
        ry = multi * (R[0, 2] - R[2, 0]) * theta * 180/math.pi
        rz = multi * (R[1, 0] - R[0, 1]) * theta * 180/math.pi
        print rx, ry, rz

        # Rotate around tool centre point defined by tcp_2
        current_Pose = ic.get_ur_position(c,1)
        demand_Pose = {"x":current_Pose[0],"y":current_Pose[1],"z":current_Pose[2],"rx":rx,"ry":ry,"rz":rz}
        msg = ic.safe_ur_move(c,Pose=dict(demand_Pose),CMD=8)

    while True:
        ipt = ser_ee.readline()
        print ipt
        if ipt == "done\r\n":
            break
    timeout = ser_ee.readline()
    print "timeout: ", timeout
    ser_ee.flush
