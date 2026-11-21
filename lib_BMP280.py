
"""
BMP280 センサーライブラリ
MicroPython / Raspberry Pi Pico W
2023/05/10
2026/11/19 エラー対策・WDT対策
元の BMP280 クラスと関数名を維持。
bmp280_dataRead() の呼び出し方法を維持。
温度・気圧を一度のI2C読み取りで取得。
センサー初期化・通信エラーに対応。
気圧990hPa未満の場合は1回だけ再測定。
エラー時は (None, None) を返す。
Pico WのI2Cタイムアウトを100msに設定。
不要な再初期化と通信を削減。
無限リトライを排除。
"""

# Author David Stenwall (david at stenwall.io)
# https://github.com/dafvid/micropython-bmp280
# 
"""
MIT License

Copyright (c) 2018 David Stenwall Wahlund

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from micropython import const
from ustruct import unpack as unp
import machine
import time
import config

# BMP280設定
BMP280_POWER_SLEEP = const(0)
BMP280_POWER_FORCED = const(1)
BMP280_POWER_NORMAL = const(3)
BMP280_SPI3W_ON = const(1)
BMP280_SPI3W_OFF = const(0)
BMP280_TEMP_OS_SKIP = const(0)
BMP280_TEMP_OS_1 = const(1)
BMP280_TEMP_OS_2 = const(2)
BMP280_TEMP_OS_4 = const(3)
BMP280_TEMP_OS_8 = const(4)
BMP280_TEMP_OS_16 = const(5)
BMP280_PRES_OS_SKIP = const(0)
BMP280_PRES_OS_1 = const(1)
BMP280_PRES_OS_2 = const(2)
BMP280_PRES_OS_4 = const(3)
BMP280_PRES_OS_8 = const(4)
BMP280_PRES_OS_16 = const(5)
BMP280_STANDBY_0_5 = const(0)
BMP280_STANDBY_62_5 = const(1)
BMP280_STANDBY_125 = const(2)
BMP280_STANDBY_250 = const(3)
BMP280_STANDBY_500 = const(4)
BMP280_STANDBY_1000 = const(5)
BMP280_STANDBY_2000 = const(6)
BMP280_STANDBY_4000 = const(7)
BMP280_IIR_FILTER_OFF = const(0)
BMP280_IIR_FILTER_2 = const(1)
BMP280_IIR_FILTER_4 = const(2)
BMP280_IIR_FILTER_8 = const(3)
BMP280_IIR_FILTER_16 = const(4)
BMP280_OS_ULTRALOW = const(0)
BMP280_OS_LOW = const(1)
BMP280_OS_STANDARD = const(2)
BMP280_OS_HIGH = const(3)
BMP280_OS_ULTRAHIGH = const(4)
BMP280_CASE_HANDHELD_LOW = const(0)
BMP280_CASE_HANDHELD_DYN = const(1)
BMP280_CASE_WEATHER = const(2)
BMP280_CASE_FLOOR = const(3)
BMP280_CASE_DROP = const(4)
BMP280_CASE_INDOOR = const(5)

# オーバーサンプリング設定
_BMP280_OS_MATRIX = [
    [BMP280_PRES_OS_1, BMP280_TEMP_OS_1, 7],
    [BMP280_PRES_OS_2, BMP280_TEMP_OS_1, 9],
    [BMP280_PRES_OS_4, BMP280_TEMP_OS_1, 14],
    [BMP280_PRES_OS_8, BMP280_TEMP_OS_1, 23],
    [BMP280_PRES_OS_16, BMP280_TEMP_OS_2, 44]
]

# 使用条件設定
_BMP280_CASE_MATRIX = [
    [BMP280_POWER_NORMAL, BMP280_OS_ULTRAHIGH, BMP280_IIR_FILTER_4, BMP280_STANDBY_62_5],
    [BMP280_POWER_NORMAL, BMP280_OS_STANDARD, BMP280_IIR_FILTER_16, BMP280_STANDBY_0_5],
    [BMP280_POWER_FORCED, BMP280_OS_ULTRALOW, BMP280_IIR_FILTER_OFF, BMP280_STANDBY_0_5],
    [BMP280_POWER_NORMAL, BMP280_OS_STANDARD, BMP280_IIR_FILTER_4, BMP280_STANDBY_125],
    [BMP280_POWER_NORMAL, BMP280_OS_LOW, BMP280_IIR_FILTER_OFF, BMP280_STANDBY_0_5],
    [BMP280_POWER_NORMAL, BMP280_OS_ULTRAHIGH, BMP280_IIR_FILTER_16, BMP280_STANDBY_0_5]
]

# レジスタ
_BMP280_REGISTER_ID = const(0xD0)
_BMP280_REGISTER_RESET = const(0xE0)
_BMP280_REGISTER_STATUS = const(0xF3)
_BMP280_REGISTER_CONTROL = const(0xF4)
_BMP280_REGISTER_CONFIG = const(0xF5)
_BMP280_REGISTER_DATA = const(0xF7)

# --------------------------------------------------
# BMP280クラス
# --------------------------------------------------
class BMP280:
    def __init__(self, i2c_bus, addr=0x76, use_case=BMP280_CASE_HANDHELD_DYN):
        self._bmp_i2c = i2c_bus
        self._i2c_addr = addr
        # 校正データを一括読み込み
        d = self._read(0x88, 24)
        if len(d) != 24:
            raise OSError("BMP280校正データ異常")
        c = unp('<HhhHhhhhhhhh', d)
        (self._T1, self._T2, self._T3, self._P1,
         self._P2, self._P3, self._P4, self._P5,
         self._P6, self._P7, self._P8, self._P9) = c
        if self._P1 == 0:
            raise ValueError("BMP280校正データ異常")
        self._t_raw = 0
        self._p_raw = 0
        self._t_fine = 0
        self._t = 0
        self._p = 0
        self.read_wait_ms = 0
        self._new_read_ms = 200
        self._last_read_ts = 0
        if use_case is not None:
            self.use_case(use_case)

    def _read(self, addr, size=1):
        return self._bmp_i2c.readfrom_mem(self._i2c_addr, addr, size)

    def _write(self, addr, b_arr):
        if not isinstance(b_arr, (bytearray, bytes)):
            b_arr = bytearray([b_arr])
        return self._bmp_i2c.writeto_mem(self._i2c_addr, addr, b_arr)

    def _gauge(self):
        d = self._read(_BMP280_REGISTER_DATA, 6)
        if len(d) != 6:
            raise OSError("BMP280読み取りデータ異常")
        self._p_raw = (d[0] << 12) | (d[1] << 4) | (d[2] >> 4)
        self._t_raw = (d[3] << 12) | (d[4] << 4) | (d[5] >> 4)
        self._t_fine = 0
        self._t = 0
        self._p = 0

    def reset(self):
        self._write(_BMP280_REGISTER_RESET, 0xB6)

    def load_test_calibration(self):
        self._T1 = 27504
        self._T2 = 26435
        self._T3 = -1000
        self._P1 = 36477
        self._P2 = -10685
        self._P3 = 3024
        self._P4 = 2855
        self._P5 = 140
        self._P6 = -7
        self._P7 = 15500
        self._P8 = -14600
        self._P9 = 6000

    def load_test_data(self):
        self._t_raw = 519888
        self._p_raw = 415148
        self._t_fine = 0
        self._t = 0
        self._p = 0

    def print_calibration(self):
        for name in ('T1', 'T2', 'T3', 'P1', 'P2', 'P3',
                     'P4', 'P5', 'P6', 'P7', 'P8', 'P9'):
            v = getattr(self, '_' + name)
            print("{}: {} {}".format(name, v, type(v)))

    def _calc_t_fine(self):
        if self._t_fine == 0:
            var1 = (((self._t_raw >> 3) - (self._T1 << 1)) * self._T2) >> 11
            var2 = (((((self._t_raw >> 4) - self._T1) ** 2) >> 12) * self._T3) >> 14
            self._t_fine = var1 + var2

    def _calculate(self):
        self._calc_t_fine()
        self._t = ((self._t_fine * 5 + 128) >> 8) / 100.0
        var1 = self._t_fine - 128000
        var2 = var1 * var1 * self._P6
        var2 += (var1 * self._P5) << 17
        var2 += self._P4 << 35
        var1 = ((var1 * var1 * self._P3) >> 8) + ((var1 * self._P2) << 12)
        var1 = (((1 << 47) + var1) * self._P1) >> 33
        if var1 == 0:
            self._p = 0
            return
        p = 1048576 - self._p_raw
        p = int((((p << 31) - var2) * 3125) / var1)
        var1 = (self._P9 * (p >> 13) * (p >> 13)) >> 25
        var2 = (self._P8 * p) >> 19
        p = ((p + var1 + var2) >> 8) + (self._P7 << 4)
        self._p = p / 256.0

    @property
    def temperature(self):
        self._gauge()
        self._calculate()
        return self._t

    @property
    def pressure(self):
        self._gauge()
        self._calculate()
        return self._p

    def _write_bits(self, address, value, length, shift=0):
        d = self._read(address)[0]
        mask = ((1 << length) - 1) << shift
        d = (d & ~mask) | ((value << shift) & mask)
        self._write(address, d)

    def _read_bits(self, address, length, shift=0):
        d = self._read(address)[0]
        return (d >> shift) & ((1 << length) - 1)

    @property
    def standby(self):
        return self._read_bits(_BMP280_REGISTER_CONFIG, 3, 5)

    @standby.setter
    def standby(self, v):
        if not 0 <= v <= 7:
            raise ValueError("standby設定範囲エラー")
        self._write_bits(_BMP280_REGISTER_CONFIG, v, 3, 5)

    @property
    def iir(self):
        return self._read_bits(_BMP280_REGISTER_CONFIG, 3, 2)

    @iir.setter
    def iir(self, v):
        if not 0 <= v <= 4:
            raise ValueError("iir設定範囲エラー")
        self._write_bits(_BMP280_REGISTER_CONFIG, v, 3, 2)

    @property
    def spi3w(self):
        return self._read_bits(_BMP280_REGISTER_CONFIG, 1)

    @spi3w.setter
    def spi3w(self, v):
        if v not in (0, 1):
            raise ValueError("spi3w設定エラー")
        self._write_bits(_BMP280_REGISTER_CONFIG, v, 1)

    @property
    def temp_os(self):
        return self._read_bits(_BMP280_REGISTER_CONTROL, 3, 5)

    @temp_os.setter
    def temp_os(self, v):
        if not 0 <= v <= 5:
            raise ValueError("temp_os設定範囲エラー")
        self._write_bits(_BMP280_REGISTER_CONTROL, v, 3, 5)

    @property
    def press_os(self):
        return self._read_bits(_BMP280_REGISTER_CONTROL, 3, 2)

    @press_os.setter
    def press_os(self, v):
        if not 0 <= v <= 5:
            raise ValueError("press_os設定範囲エラー")
        self._write_bits(_BMP280_REGISTER_CONTROL, v, 3, 2)

    @property
    def power_mode(self):
        return self._read_bits(_BMP280_REGISTER_CONTROL, 2)

    @power_mode.setter
    def power_mode(self, v):
        if not 0 <= v <= 3:
            raise ValueError("power_mode設定範囲エラー")
        self._write_bits(_BMP280_REGISTER_CONTROL, v, 2)

    @property
    def is_measuring(self):
        return bool(self._read_bits(_BMP280_REGISTER_STATUS, 1, 3))

    @property
    def is_updating(self):
        return bool(self._read_bits(_BMP280_REGISTER_STATUS, 1))

    @property
    def chip_id(self):
        return self._read(_BMP280_REGISTER_ID, 1)

    @property
    def in_normal_mode(self):
        return self.power_mode == BMP280_POWER_NORMAL

    def force_measure(self):
        self.power_mode = BMP280_POWER_FORCED

    def normal_measure(self):
        self.power_mode = BMP280_POWER_NORMAL

    def sleep(self):
        self.power_mode = BMP280_POWER_SLEEP

    def use_case(self, uc):
        if not 0 <= uc <= 5:
            raise ValueError("use_case設定範囲エラー")
        pm, oss, iir, sb = _BMP280_CASE_MATRIX[uc]
        p_os, t_os, self.read_wait_ms = _BMP280_OS_MATRIX[oss]
        self._write(_BMP280_REGISTER_CONFIG, (iir << 2) | (sb << 5))
        self._write(_BMP280_REGISTER_CONTROL, pm | (p_os << 2) | (t_os << 5))

    def oversample(self, oss):
        if not 0 <= oss <= 4:
            raise ValueError("oversample設定範囲エラー")
        p_os, t_os, self.read_wait_ms = _BMP280_OS_MATRIX[oss]
        self._write_bits(_BMP280_REGISTER_CONTROL, p_os | (t_os << 3), 6)

# --------------------------------------------------
# BMP280データ取得
# --------------------------------------------------
def bmp280_dataRead():
    try:
        # 設定取得
        i2c_no, SDA_pin = config.i2c_ini()
        T_hosei, H_hosei, P_hosei = config.hosei()
        # I2C初期化（Pico W：タイムアウト100ms）
        i2c = machine.I2C(
            i2c_no,
            sda=machine.Pin(SDA_pin),
            scl=machine.Pin(SDA_pin + 1),
            timeout=100000
        )
        # I2Cスキャンは1回だけ
        devices = i2c.scan()
        if 0x76 in devices:
            addr = 0x76
        elif 0x77 in devices:
            addr = 0x77
        else:
            raise OSError("BMP280が見つかりません")
        # センサー初期化
        bmp = BMP280(i2c, addr)
        if bmp.chip_id[0] != 0x58:
            raise OSError("BMP280ではありません")
        # 温度・気圧を同時取得
        bmp._gauge()
        bmp._calculate()
        temp = bmp._t
        press = bmp._p / 100.0
        # 気圧が低い場合は1回だけ再測定
        if press < 990:
            time.sleep_ms(400)
            bmp._gauge()
            bmp._calculate()
            temp = bmp._t
            press = bmp._p / 100.0
        return temp, press + P_hosei
    except Exception as e:
        print("BMP280読み取りエラー:", e)
        return None, None

# --------------------------------------------------
# 動作確認
# --------------------------------------------------
def main():
    while True:
        temp, press = bmp280_dataRead()
        if temp is not None and press is not None:
            print("Temperature: {:.2f} °C".format(temp))
            print("Pressure: {:.2f} hPa".format(press))
        else:
            print("BMP280データ取得失敗")
        time.sleep(2)

if __name__ == '__main__':
    main()
