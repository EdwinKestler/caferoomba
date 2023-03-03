#!/usr/bin/env python
"""_type_: _description_: this is the continuous_drive.py: 

"""
import sys
from robot_drive import Robot

def main():
    # Initialize the robot
    robot = Robot(left_gpio=19, right_gpio=13)
    drive = robot.drive
    
    while True:
        # Read keyboard input
        char = robot.getch()
        
        # Get the next state from the FSM transitions table
        next_state = robot.transitions.get((robot.state, char))
        
        # If the next state is valid, transition to it and perform the corresponding robot action
        if next_state:
            if next_state == "stop":
                drive.stop()
            else:
                #if robot.state != "stop":
                    #xdrive.stop()
                robot.state = next_state
                if robot.state == "forward":
                    drive.steering(speed=50)
                elif robot.state == "reverse":
                    drive.steering(speed=-50)
                elif robot.state == "left":
                    drive.steering(speed=50, direction=90)
                elif robot.state == "right":
                    drive.steering(speed=50, direction=-90)
                elif robot.state == "forward_left":
                    drive.steering(speed=50, direction=45)
                elif robot.state == "forward_right":
                    drive.steering(speed=50, direction=-45)
                elif robot.state == "reverse_left":
                    drive.steering(speed=-50, direction=90)
                elif robot.state == "reverse_right":
                    drive.steering(speed=-50, direction=-90)
                elif robot.state == "left_stop":
                    drive.steering(speed=0, direction=90)
                elif robot.state == "right_stop":
                    drive.steering(speed=0, direction=-90)
        elif char == "z":
            sys.exit()
        elif char == "x":
            drive.stop()

if __name__ == "__main__":
    main()