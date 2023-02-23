"""_summary_; this creates a flask application on port 5000 serves index.html with the intention of controlling some servos as described, forward,backward, left, rigt, and stop
"""
from flask import Flask, render_template, request
import time
import RPi.GPIO as GPIO

pin1 = 32 # Pin de pwm del motor 1
pin2 = 33 # Pin de pwm del motor 2

class Motores:
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

    def avanzar(self):
        self.pwm.ChangeDutyCycle(2.5)
        self.pwm2.ChangeDutyCycle(12.5)

    def parar(self):
        self.pwm.ChangeDutyCycle(6.9)
        self.pwm2.ChangeDutyCycle(6.9)

    def derecha(self):
        self.pwm.ChangeDutyCycle(2.5)
        self.pwm2.ChangeDutyCycle(6.9)

    def izquierda(self):
        self.pwm.ChangeDutyCycle(6.9)
        self.pwm2.ChangeDutyCycle(12.5)

    def retroceder(self):
        self.pwm.ChangeDutyCycle(12.5)
        self.pwm2.ChangeDutyCycle(2.5)

    def stop(self):
        self.pwm.stop()
        self.pwm2.stop()
        GPIO.cleanup()

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/forward")
def avanzar():
    robot.avanzar()
    time.sleep(1)
    robot.parar()
    return render_template("index.html")

@app.route("/backward")
def retroceder():
    robot.retroceder()
    time.sleep(1)
    robot.parar()
    return render_template("index.html")

@app.route("/right")
def derecha():
    robot.derecha()
    time.sleep(1)
    robot.parar()
    return render_template("index.html")

@app.route("/left")
def izquierda():
    robot.izquierda()
    time.sleep(1)
    robot.parar()
    return render_template("index.html")

if __name__ == "__main__":
    robot = Motores(pin1, pin2)
    app.run(host='0.0.0.0', port=5000, debug=True)
