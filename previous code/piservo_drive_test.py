"""_summary_

        _type_: _description_: this is the continuous.py file it controls two servos epending on the key pressed, make it more Object Orietned programming
"""
#!/usr/bin/env python

import sys, tty, termios, time, pigpio
from piservo import Servo

# Initialize the Drive object with the appropriate GPIO pins and parametersw
left_gpio  = 19
right_gpio = 13
#mycar = Drive(left_gpio, right_gpio, min_value=-65, max_value=65, min_pulse=0.5, max_pulse=2.5, frequency=50)

dit = pigpio.pi()

def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def transition_speed(current_speed, target_speed):
    if current_speed == target_speed:
        return target_speed

    diff = target_speed - current_speed
    step = 10 if abs(diff) >= 10 else abs(diff)

    if diff > 0:
        return current_speed + step
    else:
        return current_speed - step
    
def smooth_stop():
    
    if current_speed > 1:
        for i in range (60, -1, -5): 
            m_left.write(i)
            m_right.write(i)
            time.sleep(0.05)
    else:
        for i in range (-60, 1, 5):
            m_left.write(i)
            m_right.write(i)
            time.sleep(0.05)
        
    m_right.stop()
    m_left.stop()

current_speed = 0

m_left = Servo(left_gpio, min_value=-65, max_value=65, min_pulse=0.5, max_pulse=2.5, frequency=50)
m_right = Servo(right_gpio, min_value=-65, max_value=65, min_pulse=0.5, max_pulse=2.5, frequency=50)


m_right.start()
m_left.start()

while True:
    char = getch()

    print("          " + char)

    if char == "w":
        print("Forward")
        target_speed = 60
        while current_speed != target_speed:
            current_speed = transition_speed(current_speed, target_speed)
            m_left.write(current_speed)
            m_right.write(current_speed)
            time.sleep(0.1)
            
    elif char == "s":
        print("Reverse")
        target_speed = -60
        while current_speed != target_speed:
            current_speed = transition_speed(current_speed, target_speed)
            m_left.write(current_speed)
            m_right.write(current_speed)
            time.sleep(0.1)
            
            
    elif char == "a":
        print("Left")
        smooth_stop()
        
        m_left.start()
        m_left.write(60)
        time.sleep(0.1)
        m_left.stop()
        
        m_right.start()
        m_right.write(0)
        time.sleep(0.1)
        
        m_left.start()
        
        
    elif char == "d":
        print("Right")
        smooth_stop()
        
        m_right.start()
        m_right.write(60)
        time.sleep(0.1)
        m_right.stop()
        
        m_left.start()
        m_left.write(0)
        time.sleep(0.1)
        m_right.start()
                  
        
    elif char == "x":
        print("STOPPED")
        smooth_stop()
        for s in [left_gpio, right_gpio]: # stop servo pulses
            dit.set_servo_pulsewidth(s, 0)
        dit.stop()
        break

dit.stop()