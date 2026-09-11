"""_summary_: This code allows you to move a robert robot forward, sideways and backwards.;this runs on a rapsberry pi with no desktop enviroment use a web browser for the gui
"""
import time
import RPi.GPIO as GPIO

pin1 = 32 	#Pin de pwm del motor 1
pin2 = 33 	#Pin de pwm del motor 2

class motores:
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
		#time.sleep(1)

	def parar(self):
		self.pwm.ChangeDutyCycle(6.9)
		self.pwm2.ChangeDutyCycle(6.9)
		#time.sleep(1)

	def derecha(self):
		self.pwm.ChangeDutyCycle(2.5)
		self.pwm2.ChangeDutyCycle(6.9)
		#time.sleep(1)

	def izquierda(self):
		self.pwm.ChangeDutyCycle(6.9)
		self.pwm2.ChangeDutyCycle(12.5)
		#time.sleep(1)

	def retroceder(self):
		self.pwm.ChangeDutyCycle(12.5)
		self.pwm2.ChangeDutyCycle(2.5)
		#time.sleep(1)

	def stop(self):
		self.pwm.stop()
		self.pwm2.stop()
		GPIO.cleanup()
if __name__ == '__main__':

	robot = motores(pin1, pin2)

	robot.derecha()
	time.sleep(2)

	robot.izquierda()
	time.sleep(2)

	robot.parar()
	time.sleep(2)

	robot.avanzar()
	time.sleep(2)

	robot.retroceder()
	time.sleep(2)

	robot.parar()
	time.sleep(2)

	robot.stop()
