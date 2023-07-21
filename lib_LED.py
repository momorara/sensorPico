#
# v1.0

import machine
import time
led = machine.Pin('LED', machine.Pin.OUT)

def LEDonoff():
    led.on()
    time.sleep(.2)
    led.off()
    time.sleep(.5)
    
def end_LED():
    for _ in range(4):
        led.on()
        time.sleep(.5)
        led.off()
        time.sleep(.1)
    led.on()
    time.sleep(3)
    led.off()

def main():
    for i in range(5):
         LEDonoff()

if __name__=='__main__':
    main()
