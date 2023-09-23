"""
 2023/06/07
  基板上のタクトスイッチとLED の動作DEMO
   タクトスイッチを押すと点滅していたLED が 2秒間両方点灯する。
   v1.0
2023/9/23   タクトスイッチをソフトプルアップとした
"""
import machine
import time

# SW   = machine.Pin( 15, machine.Pin.IN)
SW   = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)
led1 = machine.Pin(16, machine.Pin.OUT)
led2 = machine.Pin(17, machine.Pin.OUT)

def LED1onoff():
    led1.on()
    time.sleep(.2)
    led1.off()
    time.sleep(.5)
    
def LED2onoff():
    led2.on()
    time.sleep(.2)
    led2.off()
    time.sleep(.5)

def main():
    LED1onoff()
    LED2onoff()
    while True:
        LED1onoff()
        LED2onoff()
        if SW.value() == 0:
            led1.on()
            led2.on()
            time.sleep(2)

if __name__=='__main__':
    main()
