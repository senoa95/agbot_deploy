#!/usr/bin/env python

# Import libraries:
import rospy
import math
from geometry_msgs.msg import Point32,Pose
from sensor_msgs.msg import NavSatFix
from std_msgs.msg import Float32
from utilities import Point, AckermannVehicle , PPController
import transforms3d as tf
import numpy as np
import os
import rospkg
import utm

rospack = rospkg.RosPack()


### Define constants:
pi = 3.141592653589793238

# Define global variables:
global currentPos
currentPos = Point()
global file_name
# file_name = rospy.get_param("/file_name")
file_name = "waypoints_5_7_3.txt"
# Callback function for subscriber to Position and orientation topic:

def pose_callback(data):

    global currentPos
    # rospy.loginfo(rospy.get_caller_id(), data.data)
    x = data.latitude
    y = data.longitude
    iniY,iniX, zoneNum , char = utm.from_latlon(x,y)
    currentPos.x = iniX
    currentPos.y = iniY

def heading_callback(data):
    global currentPos

    currentPos.heading =  data.z

# 1. Initialize function definition:
def initialize():

    global file_name
    # Create objects for AckermannVehicle and Pure Pursuit controller:
    mule = AckermannVehicle(2.065,4.6,2.2)
    cntrl = PPController(0,mule.length,mule.minTurningRadius,mule.maximumVelocity)

    cntrl.initialize(os.path.join(rospack.get_path("agbot_nav"),"src",file_name))

    return cntrl


# 2. Execute function definition:
def execute(cntrl):

    global currentPos
    distance2Goal = 100000000
    # Setup the ROS publishers and subscribers:
    rospy.Subscriber("/fix", NavSatFix, pose_callback)
    rospy.Subscriber("/novatel_imu", Point32, heading_callback)
    pub_steering = rospy.Publisher('steering_cmd', Float32, queue_size =10)
    pub_padel = rospy.Publisher('speed_setpoint', Float32, queue_size = 10)
    pub_goal = rospy.Publisher('/current_goalpoint',Point32,queue_size=10)
    rospy.init_node('ppcontroller', anonymous=True)

    rate = rospy.Rate(10)

    # Initialize:
    # 1. Parameters:
    threshold = 2.5
    euclideanError = 0

    # 2. Points:
    goalPoint = cntrl.wpList[cntrl.currWpIdx]

    # 3. Commands:
    command = Point32()
    stationaryCommand = Point32()

    stationaryCommand.x = 0
    stationaryCommand.y = 0

    # Loop through as long as the node is not shutdown:
    while not rospy.is_shutdown():

        # Compute the new Euclidean error:
        current_goalPoint = Point32(goalPoint.x,goalPoint.y,0)
        print('current Index: ',cntrl.currWpIdx)
        # print('waypoint list:', cntrl.wpList[:cntrl.currWpIdx])
        # current_goalPoint = [str(goalPoint.x),str(goalPoint.y),'0']
        pub_goal.publish(current_goalPoint)

        # euclideanError = math.sqrt((math.pow((goalPoint.x-currentPos.x),2) + math.pow((goalPoint.y-currentPos.y),2)))

        # Case #1:Vehicle is in the vicinity of current goal point (waypoint):
        if (distance2Goal < 0.2):

            # Make the AckermannVehicle stop where it is
            #pub.publish(stationaryCommand)

            print (" Reached Waypoint # ", cntrl.currWpIdx +1)

            # Update goal Point to next point in the waypoint list:
            cntrl.currWpIdx +=1

            if cntrl.currWpIdx < cntrl.nPts:
                goalPoint = cntrl.wpList[cntrl.currWpIdx]

            else:

                print (" --- All Waypoints have been conquered! Mission Accomplished Mr Hunt !!! --- ")
                break


            print (" New goal is: ")
            print (goalPoint.x)
            print (goalPoint.y)


        # print (" Euclidean Error = ", euclideanError , " meters")

        # Case #2:
        #if (euclideanError > threshold):
        vel, delta, distance2Goal = cntrl.compute_steering_vel_cmds(currentPos)

        #command = Point32()
        #command.x = delta
        #command.y = vel

        # Publish the computed command:
        pub_steering.publish(-delta)
        pub_padel.publish(vel)

            # Recompute the Euclidean error to see if its reducing:
            #euclideanError = math.sqrt((math.pow((goalPoint.x-currentPos.x),2) + math.pow((goalPoint.y-currentPos.y),2)))


        rate.sleep()

    rospy.spin()

if __name__ == '__main__':

    # Step 1: Initialize the Controller by reading in the list of waypoints:
    cntrl = initialize()

    # Step 2: Execute the controller in a closed loop manner
    execute(cntrl)
