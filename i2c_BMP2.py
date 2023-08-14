"""
2023/08/13  Pi用のBMP180,280確認用プログラムi2c_BMP.pyを参考に
            pico用に作りました。同じ機能なのに同じプログラムが使えないのは不便ですね。
            使い方は同じです。

"""

import machine
import time

def BMP_sensor2():
    # I2Cバスの初期化
    i2c = machine.I2C(0, scl=machine.Pin(1), sda=machine.Pin(0), freq=400000) 

    # デバイスのスキャン
    devices = i2c.scan()
    #print(devices)

    #  AHT10 の次に来るディバイスアドレスを取得する。
    for device in devices:
        #print("Found device at address: 0x{:02X}".format(device))
        #print(device )
        time.sleep_ms(500)
     #print(device )

    if device == 118 :
       return 'BMP280'
    if device == 119 :
       return 'BMP180'
    return 'no sensor'

def main():
    print(BMP_sensor2())

if __name__ == '__main__':
    main()
