#!/usr/bin/env python
"""_type_: _description_: this is the continuous_rover.py: 

"""
import sys
from robot import Robot

def main():
    # Initialize the robot
    robot = Robot(left_gpio=19, right_gpio=13)
    
    while True:
        
        # Read keyboard input
        char = robot.getch()
        
        # Get the next state from the FSM transitions table
        next_state = robot.transitions.get((robot.state, char))
        
        # If the next state is valid, transition to it and perform the corresponding robot action
        if next_state:
            if next_state == "stop":
                robot.stop()
            else:
                #if robot.state != "stop":
                    #robot.stop()
                robot.state = next_state
                if robot.state == "forward":
                    robot.forward()
                elif robot.state == "reverse":
                    robot.reverse()
                elif robot.state == "left":
                    robot.left()
                elif robot.state == "right":
                    robot.right()
                elif robot.state == "forward_left":
                    robot.forward_left()
                elif robot.state == "forward_right":
                    robot.forward_right()
                elif robot.state == "reverse_left":
                    robot.reverse_left()
                elif robot.state == "wreverse_right":
                    robot.reverse_right()
                elif robot.state == "left_stop":
                    robot.left_stop()
                elif robot.state == "right_stop":
                    robot.right_stop()
        elif char == "z":
            sys.exit()
        if char == "m":
            robot.advance_meters(3)
            robot.turn_degree_left(180)
            robot.advance_meters(3)
            robot.turn_degree_rigth(180)
        
if __name__ == "__main__":
    main()