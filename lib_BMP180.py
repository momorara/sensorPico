'''
bmp085 is a micropython module for the Bosch bmp085 sensor. It measures
temperature as well as pressure, with a high enough resolution to calculate
altitude.
data-sheet: BST-BMP085-DS000-05.pdf

The MIT License (MIT)
Copyright (c) 2014 Sebastian Plamauer, oeplse@gmail.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

2023/5/20   設定ファィルをconfig.pyとした
v1.0
'''
import config
i2c_no,SDA_pin = config.i2c_ini()
# センサー補正値
T_hosei,H_hosei,P_hosei = config.hosei()

from ustruct import unpack as unp
import math
import time

# BMP085 class
class BMP085():
    '''
    Module for the BMP085 pressure sensor.
    '''
    # init
    def __init__(self, i2c=None):
        # internal module defines
        if i2c is None:
            raise ValueError("The I2C bus must be specified")
        else:
            self._bmp_i2c = i2c
        self._bmp_addr = 119  # fix
        self.chip_id = self._bmp_i2c.readfrom_mem(self._bmp_addr, 0xD0, 2)
        self._delays = (7, 8, 14, 28)
        self._diff_sign = time.ticks_diff(1, 0)

        # read calibration data from EEPROM
        (self._AC1, self._AC2, self._AC3, self._AC4, self._AC5, self._AC6,
         self._B1, self._B2, self._MB, self._MC, self._MD) = \
            unp('>hhhHHHhhhhh',
                self._bmp_i2c.readfrom_mem(self._bmp_addr, 0xAA, 22))

        # settings to be adjusted by user
        self._oversample = 3
        self._baseline = 1013.25

        # output preset
        self._UT_raw = bytearray(2)
        self._B5 = 0
        self._MLX = bytearray(3)
        self._COMMAND = bytearray(1)
        self.gauge = self.makegauge()  # Generator instance
        for _ in range(128):
            next(self.gauge)
            time.sleep_ms(1)

    def compvaldump(self):
        '''
        Returns a list of all compensation values
        '''
        return [self._AC1, self._AC2, self._AC3, self._AC4, self._AC5,
                self._AC6, self._B1, self._B2, self._MB, self._MC, self._MD,
                self._oversample]

    # gauge raw
    def makegauge(self):
        '''
        Generator refreshing the raw measurments.
        '''
        while True:
            self._COMMAND[0] = 0x2e
            self._bmp_i2c.writeto_mem(self._bmp_addr, 0xF4, self._COMMAND)
            t_start = time.ticks_ms()
            while (time.ticks_diff(time.ticks_ms(), t_start) *
                   self._diff_sign) <= 5:  # 5mS delay
                yield None
            try:
                self._bmp_i2c.readfrom_mem_into(self._bmp_addr, 0xf6,
                                                self._UT_raw)
            except:
                yield None

            self._COMMAND[0] = 0x34 | (self._oversample << 6)
            self._bmp_i2c.writeto_mem(self._bmp_addr, 0xF4, self._COMMAND)
            t_pressure_ready = self._delays[self._oversample]
            t_start = time.ticks_ms()
            while (time.ticks_diff(time.ticks_ms(), t_start) *
                   self._diff_sign) <= t_pressure_ready:
                yield None
            try:
                self._bmp_i2c.readfrom_mem_into(self._bmp_addr, 0xf6,
                                                self._MLX)
            except:
                yield None
            yield True

    def blocking_read(self):
        if next(self.gauge) is not None:  # Discard old data
            pass
        while next(self.gauge) is None:
            pass

    @property
    def sealevel(self):
        return self._baseline

    @sealevel.setter
    def sealevel(self, value):
        if 300 < value < 1200:  # just ensure some reasonable value
            self._baseline = value

    @property
    def oversample(self):
        return self._oversample

    @oversample.setter
    def oversample(self, value):
        if value in range(4):
            self._oversample = value
        else:
            print('oversample can only be 0, 1, 2 or 3, using 3 instead')
            self._oversample = 3

    @property
    def temperature(self):
        '''
        Temperature in degree C.
        '''
        next(self.gauge)
        X1 = ((unp(">H", self._UT_raw)[0] - self._AC6) * self._AC5) >> 15
        X2 = (self._MC << 11) // (X1 + self._MD)
        self._B5 = X1 + X2
        return ((self._B5 + 8) >> 4) / 10.0

    @property
    def pressure(self):
        '''
        Pressure in hPa.
        '''
        self.temperature  # Get values for temperature AND pressure
        UP = (((self._MLX[0] << 16) + (self._MLX[1] << 8) + self._MLX[2]) >>
              (8 - self._oversample))
        B6 = self._B5 - 4000
        X1 = (self._B2 * ((B6 * B6) >> 12)) >> 11
        X2 = (self._AC2 * B6) >> 11
        B3 = (((self._AC1 * 4 + X1 + X2) << self._oversample) + 2) >> 2
        X1 = (self._AC3 * B6) >> 13
        X2 = (self._B1 * ((B6 * B6) >> 12)) >> 16
        X3 = ((X1 + X2) + 2) >> 2
        B4 = (self._AC4 * (X3 + 32768)) >> 15
        B7 = (UP - B3) * (50000 >> self._oversample)
        p = (B7 * 2) // B4
        X1 = (((p >> 8) * (p >> 8)) * 3038) >> 16
        X2 = (-7357 * p) // 65536
        return (p + (X1 + X2 + 3791) // 16) / 100


class BMP180(BMP085):
    def __init__(self, i2c=None):
        super().__init__(i2c)


# https://github.com/ramjipatel041/Raspberry-Pi-Pico-and-BMP180
from machine import Pin, I2C


def BMP180(flag):
    # err 後回復するために毎回設定する。
    i2c = I2C( i2c_no, sda = Pin(SDA_pin), scl = Pin(SDA_pin+1), freq = 400_00) #i2c detains
    bmp = BMP085(i2c)
    bmp.oversample = 2
    bmp.sealevel = 101325
    
    tempC = bmp.temperature        #get the temperature in degree celsius
    pres_hPa = bmp.pressure        #get the pressure in hpa
    #altitude = bmp.altitude        #get the altitude
    temp_f= (tempC * (9/5) + 32)   #convert the temperature value in fahrenheit
    tempC  = int(tempC*10 +0.1)/10
    pres_hPa_org = pres_hPa
    pres_hPa  = int(pres_hPa*10 +0.1)/10 + P_hosei
    if flag == 0:
        print(pres_hPa_org,pres_hPa,P_hosei)
    return tempC,pres_hPa

def main():
    for i in range(10):
        try:
            # flag 0:データプリント 1:データプリントしない
            temp,press = BMP180(0)
            print(temp,press)
        except:
            print( 'err')
        time.sleep( 2)

if __name__=='__main__':
    main()