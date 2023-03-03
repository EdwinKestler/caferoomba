import sys, tty, termios, time, pigpio
from servo import Servo

class Robot:
    
    FORWARD_TARGET_SPEED = 60
    REVERSE_TARGET_SPEED = -60
    STOP_TARGET_SPEED = 0
        
    def __init__(self, left_gpio, right_gpio):
        # Initialize the Robot object with two servo motors and GPIO pins
        self.left_gpio = left_gpio
        self.right_gpio = right_gpio
        self.m_left = Servo(left_gpio, min_value=-65, max_value=65, min_pulse=0.5, max_pulse=2.5, frequency=50)
        self.m_right = Servo(right_gpio, min_value=-65, max_value=65, min_pulse=0.5, max_pulse=2.5, frequency=50)
        
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
                        self.forward()
                    elif self.state == "reverse":
                        self.reverse()
                    elif self.state == "left":
                        self.left()
                    elif self.state == "right":
                        self.right()
                    elif self.state == "stop":
                        self.stop()
                    elif self.state == "forward_left":
                        self.forward_left()
                    elif self.state == "forward_right":
                        self.forward_right()
                    elif self.state == "reverse_left":
                        self.reverse_left()
                    elif self.state == "reverse_right":
                        self.reverse_right()
                    elif self.state == "left_stop":
                        self.left_stop()
                    elif self.state == "right_stop":
                        self.right_stop()
                else:
                    return ch
            elif ch == "z":
                sys.exit()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch
    
    def transition_speed(self, current_speed, target_speed):
        # Gradually change the speed of the robot to match the target speed
        if current_speed == target_speed:
            return target_speed

        diff = target_speed - current_speed
        step = 10 if abs(diff) >= 10 else abs(diff)

        if diff > 0:
            return current_speed + step
        else:
            return current_speed - step
    
    def smooth_stop(self):
        # Gradually stop the robot's motion
        if self.current_speed > 1:
            for i in range (60, -1, -5): 
                self.m_left.write(i)
                self.m_right.write(i)
                time.sleep(0.05)
        else:
            for i in range (-60, 1, 5):
                self.m_left.write(i)
                self.m_right.write(i)
                time.sleep(0.05)
        self.m_right.stop()
        self.m_left.stop()
    
    def forward(self):
        # Move the robot forward
        if self.current_direction != "forward":
            self.current_direction = "forward"
            print("Moving forward")
        while self.current_speed != self.FORWARD_TARGET_SPEED:
            self.current_speed = self.transition_speed(self.current_speed, self.FORWARD_TARGET_SPEED)
            self.m_left.write(self.current_speed)
            self.m_right.write(self.current_speed)
            time.sleep(0.1)
        
        if not self.servos_started:
            self.m_left.start()
            self.m_right.start()
            self.servos_started = True
    
    def forward_left(self):
        # Move the robot forward and left
        if self.current_direction != "forward_left":
            self.current_direction = "forward_left"
            print("Moving forward and left")
        while self.current_speed != self.FORWARD_TARGET_SPEED:
            self.current_speed = self.transition_speed(self.current_speed, self.FORWARD_TARGET_SPEED)
            self.m_left.write(self.current_speed)
            self.m_right.write(self.current_speed * 0.5)
            time.sleep(0.1)

        if not self.servos_started:
            self.m_left.start()
            self.m_right.start()
            self.servos_started = True
    
    def forward_right(self):
        # Move the robot forward and right
        if self.current_direction != "forward_right":
            self.current_direction = "forward_right"
            print("Moving forward and right")
        while self.current_speed != self.FORWARD_TARGET_SPEED:
            self.current_speed = self.transition_speed(self.current_speed, self.FORWARD_TARGET_SPEED)
            self.m_left.write(self.current_speed * 0.5)
            self.m_right.write(self.current_speed)
            time.sleep(0.1)

        if not self.servos_started:
            self.m_left.start()
            self.m_right.start()
            self.servos_started = True
    
    def reverse(self):
        # Move the robot backward
        if self.current_direction != "reverse":
            self.current_direction = "reverse"
            print("Moving backward")
        while self.current_speed != self.REVERSE_TARGET_SPEED:
            self.current_speed = self.transition_speed(self.current_speed, self.REVERSE_TARGET_SPEED)
            self.m_left.write(self.current_speed)
            self.m_right.write(self.current_speed)
            time.sleep(0.1)
        
        if not self.servos_started:
            self.m_left.start()
            self.m_right.start()
            self.servos_started = True
    
    def reverse_left(self):
        # Move the robot backward and left
        if self.current_direction != "reverse_left":
            self.current_direction = "reverse_left"
            print("Moving backward and left")
        while self.current_speed != self.REVERSE_TARGET_SPEED:
            self.current_speed = self.transition_speed(self.current_speed, self.REVERSE_TARGET_SPEED)
            self.m_left.write(self.current_speed)
            self.m_right.write(self.current_speed * 0.5)
            time.sleep(0.1)

        if not self.servos_started:
            self.m_left.start()
            self.m_right.start()
            self.servos_started = True
    
    def reverse_right(self):
        if self.current_direction != "reverse_right":
            self.current_direction = "reverse_right"
            print("Moving reverse right")
        while self.current_speed != self.REVERSE_TARGET_SPEED:
            self.current_speed = self.transition_speed(self.current_speed, self.REVERSE_TARGET_SPEED)
            self.m_left.write(self.current_speed)
            self.m_right.write(self.current_speed*0.6)
            time.sleep(0.1)

        if not self.servos_started:
            self.m_left.start()
            self.m_right.start()
            self.servos_started = True
    
    def left(self):
        if self.current_direction != "left":
            self.current_direction = "left"
            print("Turning left")
        # Turn the robot left
        self.smooth_stop()
        self.m_left.start()
        self.m_left.write(self.FORWARD_TARGET_SPEED)
        time.sleep(0.1)
        self.m_left.stop()
        self.m_right.start()
        self.m_right.write(self.STOP_TARGET_SPEED)
        time.sleep(0.1)
        self.m_left.start()
    
    def left_stop(self):
        if self.current_direction != "left_stop":
            self.current_direction = "left_stop"
            print("Stopping and turning left")
        self.smooth_stop()
        self.m_left.start()
        self.m_left.write(self.STOP_TARGET_SPEED)
        time.sleep(0.1)
        self.m_left.stop()
        self.m_right.start()
        self.m_right.write(self.STOP_TARGET_SPEED)
        time.sleep(0.1)
        self.m_left.start()
    
    def right(self):
        if self.current_direction != "right":
            self.current_direction = "right"
            print("Turning right")
            
        self.smooth_stop()
        self.m_right.start()
        self.m_right.write(self.FORWARD_TARGET_SPEED)
        time.sleep(0.1)
        self.m_right.stop()
        self.m_left.start()
        self.m_left.write(self.STOP_TARGET_SPEED)
        time.sleep(0.1)
        self.m_right.start()
    
    def right_stop(self):
        if self.current_direction != "right_stop":
            self.current_direction = "right_stop"
            print("Stopping and turning right")
        # Stop the robot completely and turn right
        self.smooth_stop()
        time.sleep(0.1)
        self.m_left.start()
        self.m_left.write(self.FORWARD_TARGET_SPEED)
        time.sleep(0.1)
        self.m_left.stop()
        self.m_right.start()
        self.m_right.write(self.STOP_TARGET_SPEED)
        time.sleep(0.1)
        self.m_left.start()
    
    def stop(self):
        if self.current_direction != "stop":
            self.current_direction = "stop"
            print("Stopping")
        # Stop the robot completely 
        self.smooth_stop()
        time.sleep(0.1)
        self.m_left.start()
        self.m_right.start()
        
        if not self.servos_started:
            print("Starting servos")
            self.m_left.start()
            self.m_right.start()
            self.servos_started = True