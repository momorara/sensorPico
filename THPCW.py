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
2023/6/4    LEDは点滅しているがambientにデータが来ていない事例発生
            自己リブートをmain.pyに組み込む
            リブートはAM1:10 に行う
            thonnyではエラーになるので、main.pyの時にフラグを立てる事とする。
2023/06/08  main.pyでのリブートループを抜け出せるようにした。
2023/6/10   wifi 使用/不使用を追加
2023/6/13   OLEDメッセージ表示、cpu温度追加
2023/6/17   データエラーの場合999ではなく、欠損とする。
2023/7/01   cpuT-気温 をambient d7に投げる
2023/07/14  エラー時のambientを3段階にする
2023/07/15  ambient_statの前後に10秒のsleepを入れた、stat noの整理
v1.0
2023/08/11  初期設定でも最低限の動作をするように改造
v1.1
2023/08/17  pico用にBMP180 と BMP280 を意識せずに使えるようにした
v1.2
2023/09/08  wbgtを追加して状態によりwbgtをambientに投げる。
2023/09/09  wbgtでLED点灯、冬季のウイルス警告も追加
v1.3
"""
main_py = 0 # 1の時は自己リブートを有効にする。

import time
import gc
import sys
import machine

import lib_LED
import wifi_onoff
import config

import lib_BMP1280
import lib_AHT10
import lib_Cds
import SSD1306
import lib_NTP
import lib_CPUtemp
import lib_wbgt

import ambient
# Ambient対応 
ch_ID,write_KEY  = config.ambi()
"""                チャネルID   ライトキー        """
am = ambient.Ambient(ch_ID, write_KEY)
""""""""""""""""""""""""""""""""""""""""""""""""""
measu_cycle = config.measu_cycle()
wifi = config.wifi_set ()
print( "wifi:",wifi)

led1 = machine.Pin(16, machine.Pin.OUT)
led2 = machine.Pin(17, machine.Pin.OUT)
led1.on()
time.sleep(0.5)
led2.on()
time.sleep(0.5)
led1.off()
time.sleep(0.5)
led2.off()

# データがNoneの場合は欠損処理をする
def ambient(temp,humi,press,Cds ,temp_cpu,temp_diff,wbgt,stat=1):
    #return
    if temp != None and press != None:
        res = am.send({"d1": temp,"d2":humi,"d3":press,"d4":Cds,"d5": stat,"d6":temp_cpu,"d7":temp_diff,"d8":wbgt })
    if temp == None and press != None:
        res = am.send({                     "d3":press,"d4":Cds,"d5": stat,"d6":temp_cpu,"d7":temp_diff,"d8":wbgt })
    if temp != None and press == None:
        res = am.send({"d1": temp,"d2":humi,           "d4":Cds,"d5": stat,"d6":temp_cpu,"d7":temp_diff,"d8":wbgt })
    if temp == None and press == None:
        res = am.send({                                "d4":Cds,"d5": stat,"d6":temp_cpu,"d7":temp_diff,"d8":wbgt })

def ambient_stat(stat):
    try:
        res = am.send({"d5": stat})
    except:
        pass

# エラーが2回続けば、データ欠損として、Noneとする。
def keisoku():
    try:
        temp1,humi1 = lib_AHT10.aht10(1)
        time.sleep(1)
    except:
        time.sleep(3)
        try:
            temp1,humi1 = lib_AHT10.aht10(1)
        except:
            temp1,humi1 = None,None
    try:
        temp,press1 = lib_BMP1280.BMP()
        time.sleep(1)
    except:
        time.sleep(3)
        try:
            temp,press1 = lib_BMP1280.BMP()
        except:
            temp,press1 = None,None
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
    temp,humi,press = 0,0,0
    press,temp,humi = keisoku()
    SSD1306.OLED(temp,humi,press)
    # wifi 接続
    ip_add = "no connect"
    if wifi == 1:
        ip_add = wifi_onoff.wifi_onoff('on')
        # NTP にて時刻合わせ
        lib_NTP.NTP_set()
        lib_LED.LEDonoff()
        lib_LED.end_LED()
    print("ip:",ip_add)
    SSD1306.OLED_mes(ip_add)
    time.sleep(10)
    ambient_stat(10)        # テスト　10
    time.sleep(10)

    UTC_OFFSET = 9 * 60 * 60
    while True:
        # センサー測定
        press,temp,humi = keisoku()
        Cds = lib_Cds.Cds(1)
        temp_cpu = lib_CPUtemp.CPU_temp()
        temp_diff = int((temp_cpu - temp)*10+0.5)/10

        # 夏季 暑さ指数
        try:
            wbgt = lib_wbgt.calc(temp,humi)
        except:
            wbgt = 0
        led1.off()
        time.sleep(0.3)
        led2.off()
        time.sleep(0.3)
        if (wbgt >= 25 and wbgt < 28) or wbgt >= 31 :led1.on()
        if  wbgt >= 28                              :led2.on()
        # 冬季ウイルス警報
        if temp <= 17                :led1.on()
        if temp <= 20 and humi <= 45 :led2.on()

        # 999って値が表示されたので、その場合は欠損とする。
        if temp > 100 :
            temp = None
            time.sleep(10)
            ambient_stat(6) 
            time.sleep(10)
        if humi > 100 :
            humi = None
            time.sleep(10)
            ambient_stat(7) 
            time.sleep(10)
        
        now = time.localtime(time.time() + UTC_OFFSET)
        print(now)
        print('気温:',temp,' 湿度:',humi,' 気圧:',press,' 明暗:',Cds,' cpuTEMP:',temp_cpu," deff_T:",temp_diff," WBGT:",wbgt)
        SSD1306.OLED(temp,humi,press)

        # 1つでもエラー値があれば、amientに投げない
        if press != 600 and temp != 100 and humi != 0:
            try:
                ambient(temp,humi,press,Cds,temp_cpu,temp_diff,wbgt)
                time.sleep(10)
            except:  
                time.sleep(10)
                ambient_stat(2)
                time.sleep(10)
                try:
                    ambient(temp,humi,press,Cds,temp_cpu,temp_diff,wbgt)
                    time.sleep(10)
                except:
                    time.sleep(60)
                    ambient_stat(3)
                    time.sleep(10)
                    try:
                        ambient(temp,humi,press,Cds,temp_cpu,temp_diff,wbgt)
                        time.sleep(10)
                    except:
                        time.sleep(10)
                        print('err ambient1')
                        ambient_stat(4) 
                        time.sleep(10)
                        if main_py == 1:
                            # リブート
                            machine.reset()
        else:
            try:
                time.sleep(10)
                ambient_stat(8)
                time.sleep(10)
                ambient(temp,humi,press,Cds,temp_cpu,temp_diff,wbgt) # とりあえず投げてみる
                time.sleep(10)
            except:
                print('err ambient1')
                time.sleep(10)
                ambient_stat(9)       # テスト　9
                time.sleep(10)
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

        now = time.localtime(time.time() + UTC_OFFSET)
        print("Time",now[3],":",now[4])
        # 午前1:10にリブート +9:00しているので、補正すること
        if now[3] == 5 and now[4] == 50: #5:50
            try:
                time.sleep(6) 
                ambient_stat(11)        # テスト　11
                time.sleep(10)
                if main_py == 1:
                    SSD1306.OLED_mes("reboot time")
                    time.sleep(60)      #最悪でも繰り返さない
                    # リブート
                    machine.reset()
                lib_NTP.NTP_set()
                SSD1306.OLED_mes("NTP")
                time.sleep(60)          # テスト
                ambient_stat(5)         # テスト　5
                time.sleep(10)
                print("NTP")
            except:
                time.sleep(10)
                ambient_stat(14)         # テスト　14
                time.sleep(10)

        gc.collect()  #ガーベージコレクション
        time.sleep(2)

         
if __name__=='__main__':
    # main()
    try:
        main()
    except:
        print("エラーが発生しました。")
        time.sleep(10)
        ambient_stat(12)
        time.sleep(10)
        SSD1306.OLED_mes("main err")
        time.sleep(2)
        print("main-try /main_py:",main_py)
        # 想定されていないエラーが発生してmainがこけた場合
        # ここに来て、リブートするが、エラーが継続している場合ループしてしまう。
        # そんな時は、リブートする前にbootスイッチを押すことで、プログラムを終了させる。
        for i in range(10):
            if bootSW() == 1:
                #print(bootSW())
                lib_LED.end_LED()
                sys.exit()
                main_py = 0
            lib_LED.LEDonoff()
            print("main-try /i:", i)
            mes = "main-try /i:" + str(i)
            SSD1306.OLED_mes(mes)

        if main_py == 1:
            time.sleep(10)
            ambient_stat(13) 
            time.sleep(10)
            SSD1306.OLED_mes("reboot")
            print("main-try / リブート")
            # リブート
            machine.reset()

"""
ambient_statによるエラー情報等の表示
1 通常
2 ambient送信異常 1回目
3 ambient送信異常 2回目
4 ambient送信異常 3回目
5 定時リブート未実行時NTP
6 温度異常
7 湿度異常
8 データ異常時のambient送信
9 データ異常時のambient送信異常
10 main start
11 定時リブート
12 mainエラー
13 mainエラー時のリブート
14 定時リブート失敗
"""