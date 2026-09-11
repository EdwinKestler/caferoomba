import sys, tty, termios, time, pigpio
from drive import Drive

class Robot:
    
    FORWARD_TARGET_SPEED = 60
    REVERSE_TARGET_SPEED = -60
    STOP_TARGET_SPEED = 0
        
    def __init__(self, left_gpio, right_gpio):
        # Initialize the Robot object with two servo motors and GPIO pins
        self.left_gpio = left_gpio
        self.right_gpio = right_gpio
        self.drive = Drive(left_gpio, right_gpio, min_value=-65, max_value=65, min_pulse=0.5, max_pulse=2.5, frequency=50)
        
        # Set the initial speed of the robot to 0
        self.current_speed = 0
        self.current_direction = "stop"
        
        # Initialize the pigpio object to control the GPIO pins
        self.dit = pigpio.pi()
        self.servos_started = True
        
        # Initialize the state machine
        self.state = "stop"
        self.transitions = {
            ("stop", "w"): "forward",
            ("stop", "s"): "reverse",
            ("stop", "a"): "left",
            ("stop", "d"): "right",
            ("forward", "s"): "stop",
            ("reverse", "w"): "stop",
            ("left", "d"): "stop",
            ("right", "a"): "stop",
            ("forward", "a"): "forward_left",
            ("forward", "d"): "forward_right",
            ("reverse", "a"): "reverse_left",
            ("reverse", "d"): "reverse_right",
            ("forward_left", "s"): "left_stop",
            ("forward_right", "s"): "right_stop",
            ("reverse_left", "w"): "left_stop",
            ("reverse_right", "w"): "right_stop",
            ("left_stop", "d"): "right_stop",
            ("right_stop", "a"): "left_stop",
            ("forward_left", "d"): "stop",
            ("forward_right", "a"): "stop",
            ("reverse_left", "a"): "stop",
            ("reverse_right", "d"): "stop",
            ("any", "x"): "stop",
            ("any", "w"): "stop",
            ("any", "a"): "stop",
            ("any", "s"): "stop",
            ("any", "d"): "stop"            
        }
  
    def getch(self):
        # Read keyboard input
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            # Get the next state from the FSM transitions table
            if ch in ["w", "a", "s", "d", "x"]:
                next_state = self.transitions.get((self.state, ch), self.transitions.get(("any", ch)))
                if next_state:
                    self.state = next_state
                    if self.state == "forward":
                        self.drive.steering(speed=self.FORWARD_TARGET_SPEED, direction=0)
                    elif self.state == "reverse":
                        self.drive.steering(speed=self.REVERSE_TARGET_SPEED, direction=0)
                    elif self.state == "left":
                        self.drive.steering(speed=self.STOP_TARGET_SPEED, direction=90)
                    elif self.state == "right":
                        self.drive.steering(speed=self.STOP_TARGET_SPEED, direction=-90)
                    elif self.state == "stop":
                        self.drive.stop()
                    elif self.state == "forward_left":
                        self.drive.steering(speed=self.FORWARD_TARGET_SPEED, direction=-45)
                    elif self.state == "forward_right":
                        self.drive.steering(speed=self.FORWARD_TARGET_SPEED, direction=45)
                    elif self.state == "reverse_left":
                        self.drive.steering(speed=self.REVERSE_TARGET_SPEED, direction=-45)
                    elif self.state == "reverse_right":
                        self.drive.steering(speed=self.REVERSE_TARGET_SPEED, direction=45)
                    elif self.state == "left_stop":
                        self.drive.steering(speed=self.STOP_TARGET_SPEED, direction=-90)
                    elif self.state == "right_stop":
                        self.drive.steering(speed=self.STOP_TARGET_SPEED, direction=90)
                else:
                    return ch
            elif ch == "z":
                sys.exit()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch