#!/usr/bin/env python
import roslib; roslib.load_manifest('nn_agent')
import rospy
import torch
from geometry_msgs.msg import Twist
from geometry_msgs.msg import Pose

from std_srvs.srv import Empty
from std_msgs.msg import UInt8
from gazebo_msgs.srv import GetModelState
from gazebo_msgs.srv import DeleteModel
from gazebo_msgs.srv import SetModelState
from gazebo_msgs.msg import ModelState

from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import sys, select, termios, tty, math, time

from guntis3 import run_episodic_learning

# -------------------
# temporary code from teleop_twist_keyboard

def getKey():
    tty.setraw(sys.stdin.fileno())
    select.select([sys.stdin], [], [], 0)
    key = sys.stdin.read(1)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key

moveBindings = {
        'i':(0.5,0,0,0),
        'j':(0,0,0,1),
        'l':(0,0,0,-1),
        ',':(-0.5,0,0,0)
           }

class Block:
    def __init__(self, name, relative_entity_name):
        self._name = name
        self._relative_entity_name = relative_entity_name

class NNAgent(object):
    def __init__(self):
        rospy.init_node('nn_agent')
        rospy.loginfo('Init nn_agent')
        print('Hello world from nn_agent!')

        self.steps_to_stop = 0
        self.observe = True
        self.cmd_publisher = rospy.Publisher('cmd_vel', Twist, queue_size = 1)
        self.bot_publisher = rospy.Publisher('bot', UInt8, queue_size = 1)
        self.turtlebot = Block('turtlebot3_burger','')
        self.bridge = CvBridge() # Convert ROS msg to numpy array
        self.image_array = None
        self.new_image = False
        # rospy.Subscriber('/camera1/image_raw', Image, callback=self.image_callback)
        rospy.Subscriber('camera1/image_raw', Image, callback=self.image_callback)
        # rospy.Subscriber('camera1', Image, callback=self.image_callback)
        # print('spinning')
        # rospy.spin()
        # print('spinned')

    def get_observation(self):
        while not self.new_image:
            time.sleep(0.1) 
        self.new_image = False
        # print('Received image data is: %s %s' % (self.image_array.shape, self.image_array.dtype))
        return self.image_array

    def image_callback(self, msg):
        if self.observe:
            self.observe = False
            self.image_array = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            self.new_image = True

        if self.steps_to_stop:
            self.steps_to_stop -= 1
            if not self.steps_to_stop:
                # print('Stopping')
                twist = Twist()
                twist.linear.x = 0; twist.linear.y = 0; twist.linear.z = 0;
                twist.angular.x = 0; twist.angular.y = 0; twist.angular.z = 0;            
                self.cmd_publisher.publish(twist)  
                self.observe = True          

    def envreset(self):
        twist = Twist()
        twist.linear.x = 0; twist.linear.y = 0; twist.linear.z = 0;
        twist.angular.x = 0; twist.angular.y = 0; twist.angular.z = 0;            
        self.cmd_publisher.publish(twist)                    
        rospy.wait_for_service('/gazebo/reset_world')
        reset_world = rospy.ServiceProxy('/gazebo/reset_world', Empty)
        reset_world()
        print('World reset')
        self.observe = True
        return self.get_observation()

    def closest_apple(self):
        model_coordinates = rospy.ServiceProxy('/gazebo/get_model_state', GetModelState)
        blockName = str(self.turtlebot._name)
        turtlebot_coordinates = model_coordinates(blockName, self.turtlebot._relative_entity_name)
        
        distanceList = []
        distanceMin = 10
        #for i in range (0,9):
        for i in range (1,2):
            apple = Block('cricket_ball_'+str(i), 'link')
            blockName = str(apple._name)
            apple_coordinates = model_coordinates(blockName, apple._relative_entity_name)
            distance = math.sqrt(math.pow(turtlebot_coordinates.pose.position.x - apple_coordinates.pose.position.x,2)+math.pow(turtlebot_coordinates.pose.position.y - apple_coordinates.pose.position.y,2)+math.pow(turtlebot_coordinates.pose.position.z - apple_coordinates.pose.position.z,2))
            # print '\n'
            distanceList.append(distance)
        distanceMin = min(distanceList)
        numberMin = distanceList.index(min(distanceList))
        return distanceMin, 1 # numberMin

    def try_to_pick_up_apple(self):
        reward = 0
        try:
            distanceLim = 0.50 #We should define the minimum distance to apple, where robot can pick up
            distanceMin, numberMin = self.closest_apple()
            print('Trying to pick up apple - distance %.2f, minimum to succeed %.2f' % (distanceMin, distanceLim))
            if distanceMin <= distanceLim: 
                #delete_model = rospy.ServiceProxy('/gazebo/delete_model', DeleteModel)
                new_model_state = rospy.ServiceProxy('/gazebo/set_model_state', SetModelState)
                model_state = ModelState()
                apple_name = 'cricket_ball_'+str(numberMin)
                print ('Picked %s' % apple_name)
                model_state.model_name = apple_name
                twist = Twist()
                twist.linear.x = 0
                twist.linear.y = 0
                twist.linear.z = 0
                twist.angular.x = 0 
                twist.angular.y = 0 
                twist.angular.z = 0
                model_state.twist = twist
                pose = Pose()
                pose.position.x = 0.2
                pose.position.y = -2.4 
                pose.position.z = 0.0
                pose.orientation.x = 0.0 
                pose.orientation.y = 0.0 
                pose.orientation.z = 0.0 
                pose.orientation.w = 0.0
                model_state.pose = pose
                model_state.reference_frame = 'world'
                #delete_apple = delete_model(apple_name)
                new_apple_state = new_model_state(model_state)
                reward = 1000
            else:
                reward = 0
                # reward = -1
                print ('You should come closer to the apple. Minimal distance = 0.50')
        except rospy.ServiceException as e:
            rospy.loginfo("Get Model State service call failed:  {0}".format(e))
        return reward

    def keyboard_loop(self):
        try:
            while(1):
                x = 0
                th = 0
                key = getKey()
                if (key == '\x03'):
                    break
                elif key == 'p':
                    self.try_to_pick_up_apple()
                elif key == 'r':
                    self.envreset()
                elif key in moveBindings.keys():
                    x = moveBindings[key][0]
                    th = moveBindings[key][3]
                bot_action = botBindings[key]
                print(key, bot_action)
                twist = Twist()
                twist.linear.x = x;
                twist.linear.y = 0;
                twist.linear.z = 0;
                twist.angular.x = 0;
                twist.angular.y = 0;
                twist.angular.z = th
                print(twist)
                self.steps_to_stop = 4
                self.cmd_publisher.publish(twist)
                self.bot_publisher.publish(UInt8(bot_action))

        except Exception as e:
            print(e)

    def envstep(self, action):
        distance_before, _ = self.closest_apple()
        bot_action = ord(action)
        print("Envstep runnning: '%s' / [%d]" % (action, bot_action))
        x = 0
        th = 0
        reward = 0
        if action in moveBindings.keys():
            x = moveBindings[action][0]
            th = moveBindings[action][3]
        elif action == 'p':
            reward = self.try_to_pick_up_apple()

        twist = Twist()
        twist.linear.x = x;
        twist.linear.y = 0;
        twist.linear.z = 0;
        twist.angular.x = 0;
        twist.angular.y = 0;
        twist.angular.z = th
        self.steps_to_stop = 4
        self.cmd_publisher.publish(twist)
        self.bot_publisher.publish(UInt8(bot_action))
        observation = self.get_observation()        
        distance_after, _ = self.closest_apple()  
        # reward = reward + distance_before - distance_after
        print('Closest apple was %.2f, is %.2f. Offered reward %.2f' % (distance_before, distance_after, reward))
        return (observation, reward, False, 0)

if __name__ == '__main__':
    try:
        settings = termios.tcgetattr(sys.stdin)
        agent = NNAgent()
        # agent.keyboard_loop()
        run_episodic_learning(agent.envreset, agent.envstep)
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start nn_agent node.')
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)