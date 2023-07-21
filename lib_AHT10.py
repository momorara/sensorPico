#!/usr/bin/env python
# -*- coding: utf-8 -*-
# https://www.route55go.com/self-study/pico/class/s006_ath10/
# AHT10 Library for MicroPython on ESP32
# Author: Sean Yong
# Date: 23rd December, 2019
# Version 1.0
# pico W 用に改造 2023/5/10

"""
2023/05/20  設定ファィルをconfig.pyとした
v1.0
"""
import time
from machine import I2C,Pin
import config


# センサー補正値
T_hosei,H_hosei,P_hosei = config.hosei()

i2c_no,SDA_pin = config.i2c_ini()

#CONSTANTS
AHT10_ADDRESS = 0x38 # 0111000 (7bit address)
AHT10_READ_DELAY_MS = 75 # Time it takes for AHT to collect data address=AHT10_ADDRESS):
AHT_TEMPERATURE_CONST = 200
AHT_TEMPERATURE_OFFSET = 50
KILOBYTE_CONST = 1048576
CMD_INITIALIZE = bytearray([0xE1, 0x08, 0x00])
CMD_MEASURE = bytearray([0xAC, 0x33, 0x00])
FARENHEIT_MULTIPLIER = 9/5
FARENHEIT_OFFSET = 32

class AHT10:
    def __init__(self, i2c01, sda_pin, mode=0, address=AHT10_ADDRESS):
        self.i2c=I2C(i2c01, scl=Pin(sda_pin+1), sda=Pin(sda_pin), freq=400_000)
        self.address = address
        self.i2c.writeto(address, CMD_INITIALIZE)
        self.readings_raw = bytearray(8)
        self.results_parsed = [0, 0]
        self.mode = mode # 0 for Celsius, 1 for Farenheit

    def read_raw(self):
        self.i2c.writeto(self.address, CMD_MEASURE)
        time.sleep_ms(AHT10_READ_DELAY_MS)
        self.readings_raw = self.i2c.readfrom(AHT10_ADDRESS, 6)
        self.results_parsed[0] = self.readings_raw[1] << 12 | self.readings_raw[2] << 4 | self.readings_raw[3] >> 4
        self.results_parsed[1] = (self.readings_raw[3] & 0x0F) << 16 | self.readings_raw[4] << 8 | self.readings_raw[5]

    def humidity(self):
        self.read_raw()
        return (self.results_parsed[0] / KILOBYTE_CONST) * 100 

    def temperature(self):
        self.read_raw()
        if self.mode is 0:
            return (self.results_parsed[1] / KILOBYTE_CONST) * AHT_TEMPERATURE_CONST - AHT_TEMPERATURE_OFFSET
        else:
            return ((self.results_parsed[1] / KILOBYTE_CONST) * AHT_TEMPERATURE_CONST - AHT_TEMPERATURE_OFFSET) * FARENHEIT_MULTIPLIER + FARENHEIT_OFFSET

    def set_mode(self, mode):
        if mode is not (0 or 1):
            raise ValueError('Mode must be either 0 for Celsius or 1 Farenheit')
        self.mode = mode

    def print(self):
        print("Temperature: " + str(self.temperature()) + ("C","F")[self.mode] + ", Humidity: " + str(self.humidity()))
    
# 以下は、上記classを使うためのオリジナル部分
aht=AHT10(i2c_no,SDA_pin, 0)       # instance (i2c01, sda_pin, mod)
"""
i2c01   0 or 1 
sda_pin GPIOpin No
mod     0:摂氏 1:華氏
"""
time.sleep(0.2)

def  aht10(flag):

    time.sleep(0.2)

    temp = aht.temperature()
    humi = aht.humidity()
    # 読み取った値を表示 flag = 0
    if flag == 0:
        print('RH%=',humi,'TC=',temp)
    temp  = int(temp*10 +0.1)/10 + T_hosei
    humi  = int(humi*10 +0.1)/10 + H_hosei
    return temp,humi

def main():
    for i in range(5):
        temp,humi = aht10(0)
        print(temp,humi)
        time.sleep(1)

if __name__=='__main__':
    main()
    