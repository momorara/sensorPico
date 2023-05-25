# -*- coding: utf-8 -*-
#!/usr/bin/python3
# 2023/05/04
# AHT10とBMP180を連続して読み取り
# ambientにデータを投げます。
# OSError: [Errno 12] ENOMEMがでたので、ガーベージコレクションを入れてみた。
"""
2023/5/7    lib化
2023/5/9    Cds追加
2023/5/10   SSD1306追加
2023/5/18   センサー測定を改良
2023/5/19   OLED修正
2023/5/20   測定周期設定、設定ファィルをconfig.pyとした
2023/5/20   SSD1306が無くても大丈夫にしたので、プログラムをOLED有無で統合した。
            bootスイッチが押されたらプログラム終了
2023/5/23   午前1:00にNTPにて時刻合わせ
"""
import time
import gc
import sys

import lib_LED
import wifi_onoff
import config

import lib_BMP180
import lib_AHT10
import lib_Cds
import SSD1306
import lib_NTP

import ambient
# Ambient対応 
ch_ID,write_KEY  = config.ambi()
"""                チャネルID   ライトキー        """
am = ambient.Ambient(ch_ID, write_KEY)
""""""""""""""""""""""""""""""""""""""""""""""""""

measu_cycle = config.measu_cycle()

def ambient(temp,humi,press,Cds):
    #res = am.send({"d1": temp})
    res = am.send({"d1": temp,"d2":humi,"d3":press,"d4":Cds})

# 与えられた3つの数字のうち近い2つの平均を返す。
# ただし、全ての誤差が0.3未満の場合は、3つの平均をかえす。
def three2one(x1,x2,x3):
    ave = (x1 + x2 + x3) /3 
    dx1ave,dx2ave,dx3ave = abs(ave - x1),abs(ave - x2),abs(ave - x3)
    #print(dx1ave,dx2ave,dx3ave )
    print( x1,x2,x3 )
    if dx1ave < 0.3 and dx2ave < 0.3 and dx3ave < 0.3:
        if dx1ave > dx2ave :
            if dx1ave > dx3ave:
                result = ( x2 + x3 ) / 2
            else:
                result = ( x1 + x2 ) / 2
        else:
            if dx2ave > dx3ave:
                result = ( x1 + x3 ) / 2
            else:
                result = ( x1 + x2 ) / 2
    else: 
        result = ( x1 + x2 + x3 ) / 3
    return int(result*10+0.5) / 10

def keisoku():
    try:
        temp1,humi1 = lib_AHT10.aht10(1)
    except:
        temp1,humi1 = 300,-110
    try:
        temp,press1 = lib_BMP180.BMP180(1)
    except:
        press1 = 600
    time.sleep(5)
    return press1,temp1,humi1

# bootSWの状態を見る
import machine
led = machine.Pin('LED', machine.Pin.OUT)
BOOTSEL_PIN = 22
bootsel_button = machine.Pin(BOOTSEL_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
def bootSW():
    if rp2.bootsel_button() == 1:
        return 1
    else:
        return 0

def main():
    lib_LED.LEDonoff()
    # wifi 接続
    wifi_onoff.wifi_onoff('on')
    # NTP にて時刻合わせ
    lib_NTP.NTP_set()
    lib_LED.LEDonoff()

    try:
        temp,humi,press = 0,0,0
        SSD1306.OLED(temp,humi,press)
    except:
        pass

    while True:
         # 5秒毎に計測し、ハズレ値を外して平均する。
        press1,temp1,humi1 = keisoku()
        press2,temp2,humi2 = keisoku()
        press3,temp3,humi3 = keisoku()
        temp  = three2one(temp1,temp2,temp3)
        humi  = three2one(humi1,humi2,humi3) 
        press = three2one(press1,press2,press3)

        if temp  > 100: temp  = 100
        if humi  <   0: humi  = 0
        if press < 900: press = 600

        Cds = lib_Cds.Cds(1)

        UTC_OFFSET = 9 * 60 * 60
        now = time.localtime(time.time() + UTC_OFFSET)
        print(now)
        print('気温:',temp,'　湿度:',humi,'　気圧:',press,'　明暗:',Cds)

        print(time.localtime()[3] )

        try:
            SSD1306.OLED(temp,humi,press)
        except:
            pass
        
        # 1つでもエラー値があれば、amientに投げない
        if press != 600 and temp != 100 and humi != 0:
            try:
                ambient(temp,humi,press,Cds)
            except:
                print('err ambient')
        else:
            print('pass ambient')


        # 次の毎正分まで待つ
        now = time.localtime()
        minute_ago = now[4]
        minute_now = now[4]
        while minute_ago == minute_now:
            time.sleep(0.2)
            now = time.localtime()
            minute_now = now[4]
            second = now[5]
            if second % 5 == 1:
                lib_LED.LEDonoff()
            # bootスイッチが押されたらプログラム終了
            if bootSW() == 1:
                #print(bootSW())
                lib_LED.end_LED()
                sys.exit()
        print('-')

        # measu_cycleで割り切れる分になるまで待つ
        while time.localtime()[4] % measu_cycle != 0:
            time.sleep(0.2)
            second = time.localtime()[5]
            if second % 5 == 1:
                lib_LED.LEDonoff()
            # bootスイッチが押されたらプログラム終了
            if bootSW() == 1:
                #print(bootSW())
                lib_LED.end_LED()
                sys.exit()
        print('%')

        # 午前1:00にNTPにて時刻合わせ +9:00なので 16
        if time.localtime()[3] == 16:
            if time.localtime()[4] == 0:
                try:
                    lib_NTP.NTP_set()
                except:
                    pass

        gc.collect()

         
if __name__=='__main__':
    main()
