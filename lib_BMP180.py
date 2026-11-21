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

"""
BMP180 センサーライブラリ
MicroPython / Raspberry Pi Pico W
BMP085互換ドライバ
2023/05/20 config.py対応
2026/11/19 エラー対策・WDT対策
MIT License
項目	改善内容
I2C通信	100msタイムアウト
チップ確認	BMP180のID確認
校正値	異常値を検出
測定待ち	最大1秒
無限ループ	タイムアウトで終了
温度・気圧	同じ測定データを使用
再試行	無限再試行なし
エラー	(None, None) を返す
"""
import config
import time
import machine
from ustruct import unpack as unp

# I2C通信タイムアウト（Pico W：100ms）
I2C_TIMEOUT = 100000
# 測定処理タイムアウト（ms）
MEASURE_TIMEOUT = 1000

# --------------------------------------------------
# BMP085 / BMP180クラス
# --------------------------------------------------
class BMP085:
    def __init__(self, i2c=None):
        if i2c is None:
            raise ValueError("I2Cバスが指定されていません")
        self._bmp_i2c = i2c
        self._bmp_addr = 0x77
        # チップID確認
        self.chip_id = self._bmp_i2c.readfrom_mem(self._bmp_addr, 0xD0, 1)
        if len(self.chip_id) != 1 or self.chip_id[0] != 0x55:
            raise OSError("BMP180が確認できません")
        self._delays = (7, 8, 14, 28)
        # 校正データ読み込み
        d = self._bmp_i2c.readfrom_mem(self._bmp_addr, 0xAA, 22)
        if len(d) != 22:
            raise OSError("校正データ読み取りエラー")
        (self._AC1, self._AC2, self._AC3, self._AC4,
         self._AC5, self._AC6, self._B1, self._B2,
         self._MB, self._MC, self._MD) = unp(">hhhHHHhhhhh", d)
        if self._AC4 == 0 or self._AC5 == 0 or self._AC6 == 0:
            raise ValueError("校正データ異常")
        self._oversample = 3
        self._baseline = 1013.25
        self._UT_raw = bytearray(2)
        self._B5 = 0
        self._MLX = bytearray(3)
        self._COMMAND = bytearray(1)
        self._sample_ready = False
        self.gauge = self.makegauge()

    def compvaldump(self):
        return [
            self._AC1, self._AC2, self._AC3,
            self._AC4, self._AC5, self._AC6,
            self._B1, self._B2, self._MB,
            self._MC, self._MD, self._oversample
        ]

    # --------------------------------------------------
    # 測定ジェネレータ
    # --------------------------------------------------
    def makegauge(self):
        while True:
            # 温度測定開始
            self._COMMAND[0] = 0x2E
            self._bmp_i2c.writeto_mem(
                self._bmp_addr, 0xF4, self._COMMAND
            )
            start = time.ticks_ms()
            while time.ticks_diff(time.ticks_ms(), start) <= 5:
                yield None
            self._bmp_i2c.readfrom_mem_into(
                self._bmp_addr, 0xF6, self._UT_raw
            )
            # 気圧測定開始
            self._COMMAND[0] = 0x34 | (self._oversample << 6)
            self._bmp_i2c.writeto_mem(
                self._bmp_addr, 0xF4, self._COMMAND
            )
            start = time.ticks_ms()
            wait_ms = self._delays[self._oversample]
            while time.ticks_diff(time.ticks_ms(), start) <= wait_ms:
                yield None
            self._bmp_i2c.readfrom_mem_into(
                self._bmp_addr, 0xF6, self._MLX
            )
            self._sample_ready = True
            yield True

    # --------------------------------------------------
    # 測定完了待ち（最大1秒）
    # --------------------------------------------------
    def blocking_read(self):
        self._sample_ready = False
        start = time.ticks_ms()
        while True:
            if time.ticks_diff(time.ticks_ms(), start) >= MEASURE_TIMEOUT:
                raise OSError("BMP180測定タイムアウト")
            result = next(self.gauge)
            if result is True:
                return True
            time.sleep_ms(1)

    @property
    def sealevel(self):
        return self._baseline

    @sealevel.setter
    def sealevel(self, value):
        if 300 < value < 1200:
            self._baseline = value
        else:
            raise ValueError("海面気圧設定範囲エラー")

    @property
    def oversample(self):
        return self._oversample

    @oversample.setter
    def oversample(self, value):
        if value not in (0, 1, 2, 3):
            raise ValueError("oversampleは0～3を指定してください")
        self._oversample = value

    # --------------------------------------------------
    # 温度取得
    # --------------------------------------------------
    @property
    def temperature(self):
        self.blocking_read()
        UT = unp(">H", self._UT_raw)[0]
        X1 = ((UT - self._AC6) * self._AC5) >> 15
        denominator = X1 + self._MD
        if denominator == 0:
            self._sample_ready = False
            raise ValueError("温度計算エラー")
        X2 = (self._MC << 11) // denominator
        self._B5 = X1 + X2
        return ((self._B5 + 8) >> 4) / 10.0

    # --------------------------------------------------
    # 気圧取得
    # --------------------------------------------------
    @property
    def pressure(self):
        # 温度と気圧を同じ測定データから計算
        if not self._sample_ready:
            self.temperature
        UP = (
            (self._MLX[0] << 16) |
            (self._MLX[1] << 8) |
            self._MLX[2]
        ) >> (8 - self._oversample)
        B6 = self._B5 - 4000
        X1 = (self._B2 * ((B6 * B6) >> 12)) >> 11
        X2 = (self._AC2 * B6) >> 11
        B3 = (
            ((self._AC1 * 4 + X1 + X2)
             << self._oversample) + 2
        ) >> 2
        X1 = (self._AC3 * B6) >> 13
        X2 = (self._B1 * ((B6 * B6) >> 12)) >> 16
        X3 = (X1 + X2 + 2) >> 2
        B4 = (self._AC4 * (X3 + 32768)) >> 15
        if B4 == 0:
            self._sample_ready = False
            raise ValueError("気圧計算エラー：B4=0")
        B7 = (UP - B3) * (50000 >> self._oversample)
        p = (B7 * 2) // B4
        X1 = (((p >> 8) * (p >> 8)) * 3038) >> 16
        X2 = (-7357 * p) // 65536
        self._sample_ready = False
        return (p + (X1 + X2 + 3791) // 16) / 100.0


# BMP180クラス（元の互換性維持）
class BMP180(BMP085):
    def __init__(self, i2c=None):
        super().__init__(i2c)


# --------------------------------------------------
# BMP180データ取得関数
# --------------------------------------------------
def BMP180(flag):
    try:
        # I2C設定取得
        i2c_no, SDA_pin = config.i2c_ini()
        # 補正値取得
        T_hosei, H_hosei, P_hosei = config.hosei()
        # I2C初期化（Pico W：タイムアウト100ms）
        i2c = machine.I2C(
            i2c_no,
            sda=machine.Pin(SDA_pin),
            scl=machine.Pin(SDA_pin + 1),
            freq=100000,
            timeout=I2C_TIMEOUT
        )
        # センサー初期化
        bmp = BMP085(i2c)
        bmp.oversample = 2
        bmp.sealevel = 1013.25
        # 温度測定
        tempC = bmp.temperature
        # 同じ測定データから気圧取得
        pres_hPa_org = bmp.pressure
        # 温度・気圧補正
        tempC = int(tempC * 10 + 0.1) / 10
        pres_hPa = int(pres_hPa_org * 10 + 0.1) / 10 + P_hosei
        if flag == 0:
            print(pres_hPa_org, pres_hPa, P_hosei)
        return tempC, pres_hPa
    except Exception as e:
        print("BMP180読み取りエラー:", e)
        return None, None


# --------------------------------------------------
# 動作確認
# --------------------------------------------------
def main():
    for i in range(10):
        # flag 0：データ表示、1：補正値表示なし
        temp, press = BMP180(0)
        if temp is not None:
            print(temp, press)
        else:
            print("BMP180データ取得失敗")
        time.sleep(2)

if __name__ == '__main__':
    main()
