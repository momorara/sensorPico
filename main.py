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

# ambient停止を受けて別サービスに移行
2026/11/14
2026/11/19  wdt追加

THPCW_07から　sensorPico_01_wdt と改名
"""
main_py = 0 # 1の時は自己リブートを有効にする。

# -*- coding: utf-8 -*-
#!/usr/bin/python3
# sensorPico_01.py
# AHT10 / BMP180・BMP280 / CDS / OLED / Wi-Fi / Blynk / MiniViz / MQTT
# WDT対応・エラー時の停止防止
import time
import utime
import gc
import sys
import os
import machine
import rp2
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
import blynk
import MiniViz
import wifi_connect

main_py = 0  # 1の時は自己リブートを有効にする
WDT_TIMEOUT = 8000
WDT_FEED_INTERVAL = 250
SENSOR_RETRY = 1
SENSOR_RETRY_WAIT = 100
UTC_OFFSET = 9 * 60 * 60
wdt = None

# --------------------------------------------------
# 初期設定
# --------------------------------------------------
try:
    measu_cycle = int(config.measu_cycle())
except Exception as e:
    print("測定周期設定エラー:", e)
    measu_cycle = 1
if measu_cycle < 1 or measu_cycle > 60:
    measu_cycle = 1

try:
    wifi = int(config.wifi_set())
except Exception as e:
    print("Wi-Fi設定エラー:", e)
    wifi = 0
print("wifi:", wifi)

try:
    SSID, PASS = config.ID_PASS()
except Exception as e:
    print("Wi-Fi ID設定エラー:", e)
    SSID, PASS = None, None

# --------------------------------------------------
# WDT
# --------------------------------------------------
def wdt_feed():
    global wdt
    if wdt is not None:
        try:
            wdt.feed()
        except Exception as e:
            print("WDT feed error:", e)

def wdt_start():
    global wdt
    try:
        wdt = machine.WDT(timeout=WDT_TIMEOUT)
        wdt_feed()
        print("WDT start:", WDT_TIMEOUT, "ms")
    except Exception as e:
        wdt = None
        print("WDT start error:", e)

# WDTをフィードしながら待つ
def sleep_safe(ms):
    end_time = time.ticks_add(time.ticks_ms(), int(ms))
    while time.ticks_diff(end_time, time.ticks_ms()) > 0:
        wdt_feed()
        remain = time.ticks_diff(end_time, time.ticks_ms())
        time.sleep_ms(min(WDT_FEED_INTERVAL, max(1, remain)))
    wdt_feed()

# --------------------------------------------------
# 安全な関数呼び出し
# --------------------------------------------------
def safe_call(func, *args, default=None, name="function"):
    try:
        wdt_feed()
        result = func(*args)
        wdt_feed()
        return result
    except Exception as e:
        print(name, "error:", repr(e))
        wdt_feed()
        return default

# --------------------------------------------------
# LED初期化
# --------------------------------------------------
try:
    led1 = machine.Pin(16, machine.Pin.OUT)
    led2 = machine.Pin(17, machine.Pin.OUT)
    led1.on()
    sleep_safe(500)
    led2.on()
    sleep_safe(500)
    led1.off()
    sleep_safe(500)
    led2.off()
except Exception as e:
    print("LED初期化エラー:", e)

# --------------------------------------------------
# 日時ログ
# --------------------------------------------------
def time_stamp(no):
    try:
        t = utime.time() + UTC_OFFSET
        tm = utime.localtime(t)
        date_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d} {}".format(
            tm[0], tm[1], tm[2], tm[3], tm[4], tm[5], no
        )
        print("現在日時TS:", date_str)
        mode = "w" if no == -1 else "a"
        with open("time_stamp.txt", mode) as f:
            f.write(date_str + "\n")
        wdt_feed()
    except Exception as e:
        print("time_stamp error:", e)

# --------------------------------------------------
# センサー測定
# エラー時は1回だけ再試行する
# --------------------------------------------------
def sensor_read(func, name):
    for attempt in range(SENSOR_RETRY + 1):
        try:
            wdt_feed()
            result = func()
            wdt_feed()
            if result is not None:
                return result
            raise ValueError("センサー値がNone")
        except Exception as e:
            print(name, "error", attempt + 1, ":", repr(e))
            if attempt < SENSOR_RETRY:
                sleep_safe(SENSOR_RETRY_WAIT)
    return None

def keisoku():
    time_stamp(2)
    aht = sensor_read(lambda: lib_AHT10.aht10(1), "AHT10")
    if isinstance(aht, (tuple, list)) and len(aht) >= 2:
        temp1, humi1 = aht[0], aht[1]
    else:
        temp1, humi1 = None, None
    bmp = sensor_read(lambda: lib_BMP1280.BMP(), "BMP")
    if isinstance(bmp, (tuple, list)) and len(bmp) >= 2:
        temp_bmp, press1 = bmp[0], bmp[1]
    else:
        temp_bmp, press1 = None, None
    return press1, temp1, humi1

# --------------------------------------------------
# BOOTスイッチ
# --------------------------------------------------
def bootSW():
    try:
        return 1 if rp2.bootsel_button() else 0
    except Exception:
        return 0

def check_boot_switch():
    if bootSW() == 1:
        print("BOOTスイッチ検出: プログラム終了")
        safe_call(lib_LED.end_LED, name="end_LED")
        raise SystemExit

# --------------------------------------------------
# 数値チェック
# --------------------------------------------------
def valid_number(value):
    return isinstance(value, (int, float)) and value == value

def data_valid(temp, humi, press):
    if not all(valid_number(v) for v in (temp, humi, press)):
        return False
    if temp == 100 or humi == 0 or press == 600:
        return False
    return True

# --------------------------------------------------
# LED表示
# --------------------------------------------------
def led_status(temp, humi, wbgt):
    try:
        led1.off()
        led2.off()
        if valid_number(wbgt):
            if (25 <= wbgt < 28) or wbgt >= 31:
                led1.on()
            if wbgt >= 28:
                led2.on()
        # 冬季ウイルス警告
        if valid_number(temp) and temp <= 17:
            led1.on()
        if valid_number(temp) and valid_number(humi):
            if temp <= 20 and humi <= 45:
                led2.on()
    except Exception as e:
        print("LED表示エラー:", e)

# --------------------------------------------------
# メイン処理
# --------------------------------------------------
def main():
    # wdt_start()
    safe_call(lib_LED.LEDonoff, name="LED start")

    # 起動時センサー測定
    press, temp, humi = keisoku()
    safe_call(SSD1306.OLED, temp, humi, press, name="OLED")

    # Wi-Fi接続
    ip_add = "no connect"
    if wifi == 1:
        ip_add = safe_call(
            wifi_onoff.wifi_onoff, "on",
            default="no connect", name="Wi-Fi接続"
        )
        # NTP時刻合わせ
        safe_call(lib_NTP.NTP_set, name="NTP")
        safe_call(lib_LED.LEDonoff, name="LED")
        safe_call(lib_LED.end_LED, name="LED end")
    print("ip:", ip_add)
    safe_call(SSD1306.OLED_mes, ip_add, name="OLED message")
    sleep_safe(10000)
    
    wdt_start()
    while True:
        wdt_feed()
        time_stamp(-1)

        # ------------------------------------------
        # センサー測定
        # ------------------------------------------
        press, temp, humi = keisoku()
        Cds = safe_call(lib_Cds.Cds, 1, default=None, name="CDS")
        temp_cpu = safe_call(
            lib_CPUtemp.CPU_temp, default=None, name="CPU temperature"
        )

        if valid_number(temp_cpu) and valid_number(temp):
            temp_diff = int((temp_cpu - temp) * 10 + 0.5) / 10
        else:
            temp_diff = None

        time_stamp(1)

        # ------------------------------------------
        # WBGT
        # ------------------------------------------
        if valid_number(temp) and valid_number(humi):
            wbgt = safe_call(
                lib_wbgt.calc, temp, humi,
                default=0, name="WBGT"
            )
        else:
            wbgt = 0

        led_status(temp, humi, wbgt)
        time_stamp(2)

        # ------------------------------------------
        # 測定結果表示
        # ------------------------------------------
        now = time.localtime(time.time() + UTC_OFFSET)
        print(now)
        print(
            "気温:", temp,
            "湿度:", humi,
            "気圧:", press,
            "明暗:", Cds,
            "cpuTEMP:", temp_cpu,
            "deff_T:", temp_diff,
            "WBGT:", wbgt
        )
        safe_call(SSD1306.OLED, temp, humi, press, name="OLED")
        time_stamp(4)

        # ------------------------------------------
        # データ送信
        # それぞれ独立してエラー処理する
        # ------------------------------------------
        if data_valid(temp, humi, press):
            # Wi-Fi接続維持
            safe_call(wifi_connect.keep_alive, name="Wi-Fi keep_alive")
            wdt_feed()

            human = 0

            # Blynk
            safe_call(
                blynk.send_data,
                temp, humi, press, Cds, human,
                name="Blynk"
            )
            sleep_safe(1000)

            # MiniViz
            safe_call(
                MiniViz.send_data,
                temp, humi, press, Cds, human,
                name="MiniViz"
            )
            sleep_safe(1000)

            # MQTT
            topic = safe_call(
                mqtt_file.topic_get,
                default=None, name="MQTT topic"
            )
            if topic is not None:
                print(topic)
                safe_call(
                    mqtt_pub.mqtt_send,
                    topic, temp,
                    name="MQTT send"
                )
        else:
            print("pass data send: センサーデータ異常")
            time_stamp(2)

        time_stamp(5)

        # ------------------------------------------
        # 次の毎正分まで待つ
        # ------------------------------------------
        now = time.localtime()
        minute_ago = now[4]
        minute_now = now[4]

        while minute_ago == minute_now:
            sleep_safe(200)
            now = time.localtime()
            minute_now = now[4]
            second = now[5]
            if second % 5 == 1:
                safe_call(lib_LED.LEDonoff, name="LED")
            check_boot_switch()

        print("-")
        time_stamp(6)

        # ------------------------------------------
        # 測定周期に合う分まで待つ
        # ------------------------------------------
        while time.localtime()[4] % measu_cycle != 0:
            sleep_safe(200)
            second = time.localtime()[5]
            if second % 5 == 1:
                safe_call(lib_LED.LEDonoff, name="LED")
            check_boot_switch()

        print("%")
        time_stamp(7)

        now = time.localtime(time.time() + UTC_OFFSET)
        print("Time", now[3], ":", now[4])

        # ------------------------------------------
        # 午前5:50 定時リブート
        # ------------------------------------------
        if now[3] == 5 and now[4] == 50:
            try:
                date_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                    now[0], now[1], now[2], now[3], now[4], now[5]
                )
                print("現在日時:", date_str)
                with open("reboot.txt", "a") as f:
                    f.write(date_str + "\n")

                sleep_safe(6000)

                if main_py == 1:
                    safe_call(
                        SSD1306.OLED_mes, "reboot",
                        name="OLED reboot"
                    )
                    sleep_safe(60000)
                    with open("reboot_as.txt", "a") as f:
                        f.write("2\n")
                    machine.reset()

                safe_call(lib_NTP.NTP_set, name="定時NTP")
                safe_call(
                    SSD1306.OLED_mes, "NTP",
                    name="OLED NTP"
                )
                sleep_safe(60000)
                print("NTP")
            except Exception as e:
                print("定時処理エラー:", repr(e))
                sleep_safe(1000)

        time_stamp(8)
        gc.collect()
        wdt_feed()

# --------------------------------------------------
# 起動
# --------------------------------------------------
if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        print("プログラムを終了しました。")
        safe_call(lib_LED.end_LED, name="LED end")
    except Exception as e:
        print("メインプログラムエラー:", repr(e))
        safe_call(
            SSD1306.OLED_mes, "main err",
            name="OLED main error"
        )
        sleep_safe(2000)
        print("main-try / main_py:", main_py)

        # エラー後もBOOTスイッチで終了できるようにする
        for i in range(10):
            wdt_feed()
            if bootSW() == 1:
                safe_call(lib_LED.end_LED, name="LED end")
                raise SystemExit
            safe_call(lib_LED.LEDonoff, name="LED")
            print("main-try / i:", i)
            safe_call(
                SSD1306.OLED_mes,
                "main-try / i:" + str(i),
                name="OLED error message"
            )
            sleep_safe(500)

        if main_py == 1:
            sleep_safe(10000)
            safe_call(
                SSD1306.OLED_mes, "reboot",
                name="OLED reboot"
            )
            print("main-try / リブート")
            try:
                with open("reboot_as.txt", "a") as f:
                    f.write("3\n")
            except Exception as e:
                print("reboot log error:", e)
            machine.reset()
