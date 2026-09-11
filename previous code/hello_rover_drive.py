"""
_type_: _description_: this is hello_rover_drive.py its a flask application on port 5000 that controls a rover using two continuos servo connected to a rapberry pi on pins 32 (left servo) and 33 (right servo) using the library piServoCtl,
the Drive class and the Steering() method
"""
from flask import Flask, render_template, request
import threading
import time
from piservo import Drive

# Initialize the Drive object with the pins connected to the servos
left_gpio=12
right_gpio=13

servo_ctl = Drive(left_gpio, right_gpio, min_value=-65, max_value=65, min_pulse=0.5, max_pulse=2.5, frequency=50)

app = Flask(__name__)

# Define the servo functions
servo_functions = {
    "/forward": lambda: servo_ctl.steering(50, 0),
    "/backward": lambda: servo_ctl.steering(-50, 0),
    "/right": lambda: servo_ctl.steering(0, 50),
    "/left": lambda: servo_ctl.steering(0, -50),
    "/stop": servo_ctl.stop
}

def control_servo(servo, duration):
    servo_ctl.start()
    speed1, speed2 = 0, 0
    if servo == servo_ctl.steering(50, 0):
        speed1, speed2 = 50, 50
    elif servo == servo_ctl.steering(-50, 0):
        speed1, speed2 = -50, -50
    elif servo == servo_ctl.steering(0, 50):
        speed1, speed2 = 0, 50
    elif servo == servo_ctl.steering(0, -50):
        speed1, speed2 = 50, 0
    servo_ctl.steering(speed1, speed2)
    time.sleep(duration)
    servo_ctl.stop()

@app.route("/", methods=["GET", "POST"])
def control():
    if request.method == "POST":
        url = request.form.get("url")
        if url in servo_functions:
            t = threading.Thread(target=control_servo, args=(servo_functions[url], 1))
            t.start()
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)