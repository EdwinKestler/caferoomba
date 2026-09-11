from piservo import Servo
import time

class roverServo:
    def __init__(self, Spin,minA, maxA, minP, maxP, frq):
        self.Spin = Spin
        self.minA = minA
        self.maxA = maxA
        self.minP = minP
        self.maxP = maxP
        self.freq = frq
        self.__rvservo = Servo(Spin, min_value=minA, max_value=maxA, min_pulse=minP, max_pulse=maxP, frequency=frq)

    def left(self,centerA=180,leftAngle=360):
        self.__rvservo.start()
        self.__rvservo.write(centerA)
        time.sleep(0.5)
        self.__rvservo.write(leftAngle)
        time.sleep(0.5)
        self.__rvservo.write(centerA)
        time.sleep(0.5)
        self.__rvservo.stop()

    def right(self,centerA=180,rightAngle=0):
        self.__rvservo.start()
        self.__rvservo.write(centerA)
        time.sleep(0.5)
        self.__rvservo.write(rightAngle)
        time.sleep(0.5)
        self.__rvservo.write(centerA)
        time.sleep(0.5)
        self.__rvservo.stop()
    
    def center(self,centerA=180,leftAngle=360,rightAngle=0):
        self.__rvservo.start()
        self.__rvservo.write(centerA)
        time.sleep(0.5)
        self.__rvservo.write(leftAngle)
        time.sleep(0.5)
        self.__rvservo.write(rightAngle)
        time.sleep(0.5)
        self.__rvservo.write(centerA)
        time.sleep(0.5)
        self.__rvservo.stop()




    
    
