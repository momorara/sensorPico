"""
2023/04/25
https://sozorablog.com/raspberry-pi-pico-w-review/
のプログラムをmainから呼び出す関数としました。

CPUの持つ温度をシェルに表示
v1.0
"""
import machine
import utime
sensor_temp = machine.ADC(4)
conversion_factor = 3.3 / (65535)
 
def CPU_temp():
    reading = sensor_temp.read_u16() * conversion_factor
    temp = 27 - (reading - 0.706)/0.001721
    temp = round(temp, 1)
     #print(temp)
    utime.sleep(1)
    return temp
        
def main():
    for i in range(5):
         print(CPU_temp())

if __name__=='__main__':
    main()