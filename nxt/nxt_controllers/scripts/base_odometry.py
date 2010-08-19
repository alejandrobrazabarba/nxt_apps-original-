#!/usr/bin/env python

import roslib; roslib.load_manifest('nxt_controllers')  
import rospy
import math
import thread
import tf
from PyKDL import *
from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry
from nxt_msgs.msg import Range, JointCommand
from tf_conversions import posemath

PUBLISH_TF = False

class BaseOdometry:
    def __init__(self):
        self.initialized = False
        
        self.ns =rospy.get_namespace() + 'base_parameters/'
        # get joint name
        self.l_joint = rospy.get_param(self.ns +'l_wheel_joint')
        self.r_joint = rospy.get_param(self.ns +'r_wheel_joint')

        self.wheel_radius = rospy.get_param(self.ns +'wheel_radius', 0.022)
        self.wheel_basis = rospy.get_param(self.ns +'wheel_basis', 0.055)

        # joint interaction
        rospy.Subscriber('joint_states', JointState, self.jnt_state_cb)

        # tf broadcaster
        if PUBLISH_TF:
            self.br = tf.TransformBroadcaster()

        # publish results on topic
        self.pub = rospy.Publisher('odom', Odometry)

        self.initialized = False

    def jnt_state_cb(self, msg):
        # crates map
        position = {}
        for name, pos in zip(msg.name, msg.position):
            position[name] = pos
        
        # initialize
        if not self.initialized:
            self.r_pos = position[self.r_joint]
            self.l_pos = position[self.l_joint]
            self.pose = Frame()
            self.initialized = True
        else:
            delta_r_pos = position[self.r_joint] - self.r_pos
            delta_l_pos = position[self.l_joint] - self.l_pos
            delta_trans = (delta_r_pos + delta_l_pos)*self.wheel_radius/2.0
            delta_rot   = (delta_r_pos - delta_l_pos)*self.wheel_radius/(2.0*self.wheel_basis)
            twist = Twist(Vector(delta_trans, 0, 0),  Vector(0, 0, delta_rot))
            self.r_pos = position[self.r_joint]
            self.l_pos = position[self.l_joint]
            self.pose = addDelta(self.pose, self.pose.M * twist)
            if PUBLISH_TF:
                self.br.sendTransform(self.pose.p, self.pose.M.GetQuaternion(), rospy.Time.now(), 'base_link', 'odom')

            
            self.rot_covar = 1.0
            if delta_rot == 0:
                self.rot_covar = 0.00000000001
        
            odom = Odometry()
            odom.header.stamp = rospy.Time.now()
            odom.pose.pose = posemath.toMsg(self.pose)
            odom.pose.covariance = [0.00001, 0, 0, 0, 0, 0,
                                    0, 0.00001, 0, 0, 0, 0, 
                                    0, 0, 10.0000, 0, 0, 0,
                                    0, 0, 0, 1.00000, 0, 0,
                                    0, 0, 0, 0, 1.00000, 0,
                                    0, 0, 0, 0, 0, self.rot_covar]   
            self.pub.publish(odom)

def main():
    rospy.init_node('nxt_base_odometry')
    base_odometry = BaseOdometry()
    rospy.spin()



if __name__ == '__main__':
    main()
