"""_summary_; this is the hellorover.py file: this creates a flask application on port 5000 serves index.html with the intention of controlling some servos as described, forward,backward, left, rigt, and stop; images dont load and i get the masswage  "GET /forward HTTP/1.1" 404 - when clicking on alt link
"""
from flask import Flask, render_template, request
import threading
import time
import RPi.GPIO as GPIO

pin1 = 32 # Pin de pwm del motor 1
pin2 = 33 # Pin de pwm del motor 2

class servos:
    def __init__(self, pin1, pin2):
        self.pin1 = pin1
        self.pin2 = pin2
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin1, GPIO.OUT)
        GPIO.output(pin1, GPIO.LOW)
        self.pwm = GPIO.PWM(self.pin1, 50)
        self.pwm.start(7.5)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin2, GPIO.OUT)
        GPIO.output(pin2, GPIO.LOW)
        self.pwm2 = GPIO.PWM(self.pin2, 50)
        self.pwm2.start(7.5)

    def forward(self):
        self.pwm.ChangeDutyCycle(2.5)
        self.pwm2.ChangeDutyCycle(12.5)

    def right(self):
        self.pwm.ChangeDutyCycle(2.5)
        self.pwm2.ChangeDutyCycle(6.9)

    def left(self):
        self.pwm.ChangeDutyCycle(6.9)
        self.pwm2.ChangeDutyCycle(12.5)

    def backward(self):
        self.pwm.ChangeDutyCycle(12.5)
        self.pwm2.ChangeDutyCycle(2.5)

    def stop(self):
        self.pwm.stop()
        self.pwm2.stop()
        GPIO.cleanup()

app = Flask(__name__)

robot = servos(pin1, pin2)

servo_functions = {
    "/forward": robot.forward,
    "/backward": robot.backward,
    "/right": robot.right,
    "/left": robot.left
}

def control_servo(servo, duration):
    servo()
    time.sleep(duration)
    servo.stop()

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
    