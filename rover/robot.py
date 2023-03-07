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
        self.left_motor_current_speed = self.m_left.read()
        self.right_motor_current_speed = self.m_right.read()
        print("Robot initialized", self.left_motor_current_speed, self.right_motor_current_speed)
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
            ("stop", "x"): "stop",
            ("forward", "w"): "forward",
            ("forward", "s"): "stop",
            ("forward", "a"): "left",
            ("forward", "d"): "right",
            ("forward", "x"): "stop",
            ("reverse", "s"): "reverse",
            ("reverse", "w"): "stop",
            ("reverse", "a"): "left",
            ("reverse", "d"): "right",
            ("reverse", "x"): "stop",
            ("left", "w"): "forward",
            ("left", "s"): "reverse",
            ("left", "d"): "stop",
            ("left", "a"): "left",
            ("left", "x"): "stop",
            ("right", "w"): "forward",
            ("right", "s"): "reverse",
            ("right", "a"): "stop",
            ("right", "d"): "right",
            ("rigth", "x"): "stop",
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
                else:
                    return ch
            elif ch == "z":
                sys.exit()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch
    
    def transition_speed(self, current_speed, target_speed):
        print(f"Transitioning from {current_speed} to {target_speed}")
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
        print("Smooth Stopping")
        # Gradually stop the robot's motion
        if self.current_speed > 0:
            for i in range (self.current_speed, -1, -5): 
                self.m_left.write(i)
                self.m_right.write(i)
                time.sleep(0.02)
        else:
            for i in range (self.current_speed, 1, 5):
                self.m_left.write(i)
                self.m_right.write(i)
                time.sleep(0.02)
        self.current_speed = 0
        self.current_direction = "stop"
        self.state = "stop"
        #self.m_right.stop()
        #self.m_left.stop()
    
    def forward(self):
        print("Moving forward")
        # Gradually increase speed to FORWARD_TARGET_SPEED
        target_speed = self.FORWARD_TARGET_SPEED
        
        if self.current_speed < target_speed:
            for i in range(self.current_speed, target_speed+1, 5):
                self.m_left.write(i)
                self.m_right.write(i)
                time.sleep(0.02)
                self.current_speed = i
        else:
            print(f"Moving {self.current_direction} at speed {self.current_speed}")
            #self.m_left.write(target_speed)
            #self.m_right.write(target_speed)
            #self.current_speed = target_speed
            
        self.current_direction = "forward"
        self.state = "forward"
        print(f"Moving {self.current_direction} at speed {self.current_speed}")
    
    def reverse(self):
        print("Moving backward")
        # Move the robot backward
        while self.current_speed != self.REVERSE_TARGET_SPEED:
            self.current_speed = self.transition_speed(self.current_speed, self.REVERSE_TARGET_SPEED)
            self.m_left.write(self.current_speed)
            self.m_right.write(self.current_speed)
            time.sleep(0.1)
        
        if not self.servos_started:
            self.m_left.start()
            self.m_right.start()
            self.servos_started = True
        self.state = "reverse"
        self.current_direction = "reverse"
    
    def left(self):
        print("Turning left")
        # Turn the robot left
        if self.current_direction != "left":
            self.smooth_stop()  
            self.m_right.stop() 
            self.m_left.start() 
            for i in range(self.current_speed, self.FORWARD_TARGET_SPEED, 5):
                    self.m_left.write(i)
                    time.sleep(0.02)
                    self.current_speed = i
            time.sleep(0.01)
            self.m_right.start()
            self.state = "left"
            self.current_direction = "left"
        else:
            print("Already turning left")
        
    def right(self):
        print("Turning right")
        # Turn the robot right
        if self.current_direction != "right":
            self.smooth_stop()
            self.m_left.stop()
            self.m_right.start()
            for i in range(self.current_speed, self.FORWARD_TARGET_SPEED, 5):
                    self.m_right.write(i)
                    time.sleep(0.02)
                    self.current_speed = i
            time.sleep(0.01)
            self.m_left.start()
            self.state = "right"
            self.current_direction = "right"
        else:
            print("Already turning right")
    
    def stop(self):
        print("Stopping")
        self.left_motor_current_speed = self.m_left.read()
        self.right_motor_current_speed = self.m_right.read()
        print("current L, R speed", self.left_motor_current_speed, self.right_motor_current_speed)
        # Start the motors if they are not already started
        if not self.servos_started:
            self.m_left.start()
            self.m_right.start()
            
        if self.current_direction != "stop":
            self.current_direction = "stop"
            print("Stopping")
            # Stop the robot completely 
            self.smooth_stop()
            time.sleep(0.1)
        else:
            # already in stop mode
            print("Already in stop mode")
        self.state = "stop"
    
    def advance_meters(self,meter):
        t = meter*0.9836/0.5026 #change constants if change wheel size
        self.forward()
        time.sleep(t)
        self.smooth_stop()
        
    def turn_degree_left(self,deg):
        m = (deg * 0.017453)*0.5      # m = radians * distance_wheels
        t = m*0.9836/0.5026 #change constants if change wheel size
        self.right()
        time.sleep(t)
        self.smooth_stop()
        
    def turn_degree_rigth(self,deg):
        m = (deg * 0.017453)*0.5      # m = radians * distance_wheels
        t = m*0.9836/0.5026 #change constants if change wheel size
        self.left()
        time.sleep(t)
        self.smooth_stop()
        
        
            
        