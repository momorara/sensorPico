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
2024/08/23  mqtt対応
2025/05/07  LEDが点滅しているので、プログラムは動作しているようだが、
            ambientへの送信が止まっている時がある。
            これをなんとかする方法を考えたい。
            ・ambientでの送信後の状態を保存する。
2025/09/11  ・ambientでの送信失敗の日時をファイル保存
2025/09/17  リブート時にファィル保存
2025/10/01  ambi失敗5回でリブート
2025/10/03  リブートの場所を保存
2026/08/28  ambiリカバリ追加

THPCW_04.py  2025/10/01
THPCW_07.py  2026/08/28 ambiリカバリ追加
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

import mqtt_file
import mqtt_pub
import utime
import os

from ambient_pico import AmbientPico
import ambient_pico 

# Ambient対応 
ch_ID,write_KEY  = config.ambi()
"""                チャネルID   ライトキー        """
am = AmbientPico(ch_ID, write_KEY)
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

SSID, PASS = config.ID_PASS()

# データがNoneの場合は欠損処理をする
def ambient(temp,humi,press,Cds ,temp_cpu,temp_diff,wbgt,stat=1):

    if ambient_pico.wifi_reconnect(SSID, PASS) == True:# Wi-Fi 自動復帰

        if temp != None and press != None:
            status = am.send({"d1": temp,"d2":humi,"d3":press,"d4":Cds,"d5": stat,"d6":temp_cpu,"d7":temp_diff,"d8":wbgt })
        if temp == None and press != None:
            restatuss = am.send({                     "d3":press,"d4":Cds,"d5": stat,"d6":temp_cpu,"d7":temp_diff,"d8":wbgt })
        if temp != None and press == None:
            status = am.send({"d1": temp,"d2":humi,           "d4":Cds,"d5": stat,"d6":temp_cpu,"d7":temp_diff,"d8":wbgt })
        if temp == None and press == None:
            status = am.send({                                "d4":Cds,"d5": stat,"d6":temp_cpu,"d7":temp_diff,"d8":wbgt })
        
        if status == 200:
            print("ambient-OK")
        else:
            print("ambient-NG")

        # mqttのtopicを決定
        topic = mqtt_file.topic_get()
        print(topic)
        # topicに温度を送信
        mqtt_pub.mqtt_send(topic,temp)




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

def time_stamp(no):
    # JSTに直す（日本はUTC+9）
    t = utime.time() + 9*60*60
    tm = utime.localtime(t)
    # 日時を文字列に整形
    date_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        tm[0], tm[1], tm[2], tm[3], tm[4], tm[5]
    )
    date_str = date_str + " " + str(no)
    print("現在日時TS:", date_str)
    # ===== ファイルに保存 =====
    with open("time_stamp.txt", "a") as f:
        f.write(date_str + "\n")
    if no == -1:
        with open("time_stamp.txt", "w") as f:
            f.write(date_str + "\n")   

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
        time_stamp(-1)
        # センサー測定
        press,temp,humi = keisoku()
        Cds = lib_Cds.Cds(1)
        temp_cpu = lib_CPUtemp.CPU_temp()
        temp_diff = int((temp_cpu - temp)*10+0.5)/10
        time_stamp(1)
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
        time_stamp(2)
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
        time_stamp(3)
        now = time.localtime(time.time() + UTC_OFFSET)
        print(now)
        print('気温:',temp,' 湿度:',humi,' 気圧:',press,' 明暗:',Cds,' cpuTEMP:',temp_cpu," deff_T:",temp_diff," WBGT:",wbgt)
        SSD1306.OLED(temp,humi,press)
        time_stamp(4)
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
                            with open("reboot_as.txt", "a") as f:
                                f.write("1")
                            machine.reset()
        else:
            try:
                time.sleep(10)
                ambient_stat(8)
                time.sleep(10)
                ambient(temp,humi,press,Cds,temp_cpu,temp_diff,wbgt) # とりあえず投げてみる
                time.sleep(10)
            except:
                print('err ambient2')
                time.sleep(10)
                ambient_stat(9)       # テスト　9
                time.sleep(10)
            print('pass ambient')
        time_stamp(5)
        
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
        time_stamp(6)
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
        time_stamp(7)
        now = time.localtime(time.time() + UTC_OFFSET)
        print("Time",now[3],":",now[4])
        # 午前1:10にリブート +9:00しているので、補正すること
        if now[3] == 5 and now[4] == 50: #5:50
            
            # JSTに直す（日本はUTC+9）
            t = utime.time() + 9*60*60
            tm = utime.localtime(t)
            # 日時を文字列に整形
            date_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                tm[0], tm[1], tm[2], tm[3], tm[4], tm[5]
            )
            print("現在日時:", date_str)
            # ===== ファイルに保存 =====
            with open("reboot.txt", "a") as f:
                f.write(date_str + "\n")

            try:
                time.sleep(6) 
                ambient_stat(11)        # テスト　11
                time.sleep(10)
                if main_py == 1:
                    SSD1306.OLED_mes("reboot time")
                    time.sleep(60)      #最悪でも繰り返さない
                    # リブート
                    with open("reboot_as.txt", "a") as f:
                        f.write("2")
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
        time_stamp(8)
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
            with open("reboot_as.txt", "a") as f:
                f.write("3")
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