# -*- coding: utf-8 -*-
#!/usr/bin/python3
"""
2023/5/8    lib化
            キャリブレーション方法
            このプログラムを起動
            0:オリジナルデータが見える
            最大明るい、最大暗い時のデータをCds max,minに代入する。
2023/05/21  設定値をconfig.pyから取得
"""
from machine import ADC, Pin
import time
import config

# アナログピンを設定
analog_pin,Cds_max,Cds_min = config.Cds_ini()
#analog_pin = 26  # GP26を使用
# Cds_max = 60000
# Cds_min = 1500

# ADCオブジェクトを作成
adc = ADC(Pin(analog_pin))

def Cds(flag):
    # アナログ値を読み取り
    analog_value_org = adc.read_u16()
    analog_value = analog_value_org
    # %に変換
    if analog_value_org > Cds_max:
        analog_value = Cds_max
    if analog_value_org < Cds_min:
        analog_value = Cds_min
        
    analog_100 = int((analog_value - Cds_min) / (Cds_max - Cds_min) * 100)
    # 読み取った値を表示 flag = 0
    if flag == 0:
        print("Analog Value: ",analog_value_org,analog_value , analog_100)
    return analog_100

def main():
    for i in range(10):
         print(Cds(0))
         time.sleep(1)

if __name__=='__main__':
    main()