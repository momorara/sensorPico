
# ============================================================
# wifi_connect.py
# Raspberry Pi Pico W / MicroPython
#
# 単独実行：
#   Wi-Fi接続・接続状況監視を行う
#
# 他のプログラムから利用：
#   import wifi_connect
#   wifi_connect.connect()
#   wifi_connect.is_connected()
#   wifi_connect.show_status()
#   wifi_connect.keep_alive()
#
# ============================================================

import network
import time
import gc
import config


# ------------------------------------------------------------
# 設定
# ------------------------------------------------------------

SSID, PASSWORD = config.ID_PASS()

CONNECT_TIMEOUT = 30
RETRY_INTERVAL = 5
CHECK_INTERVAL = 1
STATUS_INTERVAL = 10

# Trueなら接続情報を定期表示
SHOW_STATUS = True

wlan = network.WLAN(network.STA_IF)

connected_time = None


# ------------------------------------------------------------
# Wi-Fi初期化
# ------------------------------------------------------------

def wifi_init():

    print("Wi-Fi初期化")

    try:
        wlan.active(False)
        time.sleep(1)

        wlan.active(True)
        time.sleep(1)

        return True

    except Exception as e:
        print("Wi-Fi初期化エラー:", repr(e))
        return False


# ------------------------------------------------------------
# 接続状態確認
# ------------------------------------------------------------

def is_connected():

    try:

        if not wlan.active():
            return False

        if not wlan.isconnected():
            return False

        ip = wlan.ifconfig()[0]

        if ip == "0.0.0.0":
            return False

        return True

    except Exception:
        return False


# ------------------------------------------------------------
# 接続情報表示
# ------------------------------------------------------------

def show_status():

    print("--------------------------------")
    print("Wi-Fi接続状況")

    if is_connected():

        try:
            ip, subnet, gateway, dns = wlan.ifconfig()

            try:
                rssi = wlan.status("rssi")
            except Exception:
                rssi = "取得不可"

            print("状態       : 接続中")
            print("SSID       :", SSID)
            print("IPアドレス :", ip)
            print("サブネット :", subnet)
            print("Gateway    :", gateway)
            print("DNS        :", dns)
            print("電波強度   :", rssi, "dBm")

            if connected_time is not None:

                elapsed = time.ticks_diff(
                    time.ticks_ms(), connected_time
                ) // 1000

                print("接続継続   :", elapsed, "秒")

        except Exception as e:
            print("情報取得エラー:", repr(e))

    else:

        print("状態       : 未接続")
        print("SSID       :", SSID)

        try:
            print("状態コード :", wlan.status())
        except Exception:
            pass

    print("--------------------------------")


# ------------------------------------------------------------
# Wi-Fi接続
# ------------------------------------------------------------

def connect():

    global connected_time

    while True:

        try:

            if is_connected():

                if connected_time is None:
                    connected_time = time.ticks_ms()

                print("Wi-Fi接続済み")
                show_status()

                return True

            print("Wi-Fi接続開始")

            if not wlan.active():
                wifi_init()

            try:
                wlan.disconnect()
            except Exception:
                pass

            wlan.connect(SSID, PASSWORD)

            start = time.ticks_ms()

            while time.ticks_diff(
                time.ticks_ms(), start
            ) < CONNECT_TIMEOUT * 1000:

                if is_connected():

                    connected_time = time.ticks_ms()

                    print("Wi-Fi接続成功")

                    show_status()

                    gc.collect()

                    return True

                time.sleep(CHECK_INTERVAL)

            print("接続タイムアウト")
            print("状態コード:", wlan.status())

        except Exception as e:

            print("Wi-Fi接続エラー:", repr(e))

        try:
            wlan.disconnect()
        except Exception:
            pass

        gc.collect()

        print(RETRY_INTERVAL, "秒後に再接続")
        time.sleep(RETRY_INTERVAL)


# ------------------------------------------------------------
# Wi-Fi接続維持
# ------------------------------------------------------------

def keep_alive():

    global connected_time

    if is_connected():
        return True

    print("Wi-Fi切断を検出")

    connected_time = None

    try:
        wlan.disconnect()
    except Exception:
        pass

    time.sleep(1)

    connect()

    return is_connected()


# ------------------------------------------------------------
# 単独実行用の監視プログラム
# ------------------------------------------------------------

def monitor():

    print("================================")
    print("Pico W Wi-Fi接続監視プログラム")
    print("================================")

    connect()

    last_status = time.ticks_ms()

    while True:

        try:

            if not is_connected():

                print("Wi-Fi切断!")
                keep_alive()

                last_status = time.ticks_ms()

            if time.ticks_diff(
                time.ticks_ms(), last_status
            ) >= STATUS_INTERVAL * 1000:

                show_status()

                last_status = time.ticks_ms()

            time.sleep(1)

        except Exception as e:

            print("監視エラー:", repr(e))

            time.sleep(3)

            keep_alive()


# ------------------------------------------------------------
# 単独実行の場合だけ監視を開始
# ------------------------------------------------------------

if __name__ == "__main__":

    monitor()



""" 別のアプリから利用する場合

import wifi_connect
import time

# Wi-Fi接続（接続できるまで待機）
wifi_connect.connect()

while True:

    # Wi-Fi接続確認・切断時は再接続
    wifi_connect.keep_alive()

    # 接続状況表示
    wifi_connect.show_status()

    # ここにセンサー読み取り・MiniViz送信処理

    time.sleep(60)
"""