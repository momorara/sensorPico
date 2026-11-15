
# ==================================================
# MiniViz_PicoW.py
# Raspberry Pi Pico W / MicroPython
# MiniVizデータ送信専用モジュール
# 2026/11/13 修正
#
# 機能
# ・MiniVizへのデータ送信
# ・HTTPエラー対応
# ・通信エラー再試行
# ・HTTP 429対応
# ・他のプログラムから関数として利用可能
#
# Wi-Fi接続・NTP時刻同期は呼び出し元で実施
# ==================================================

import time
import urequests
import random
import config
import wifi_connect


# --------------------------------------------------
# MiniViz設定
# --------------------------------------------------

TOKEN, PROJECT_ID, LABEL_KEY = config.MINIVIZ_token()

URL = "https://api.miniviz.net/api/project/{}".format(PROJECT_ID)

URL = "https://api.miniviz.net/api/project/{}?token={}".format(
    PROJECT_ID, TOKEN
)

MAX_RETRY = 3
RETRY_WAIT = 5

# --------------------------------------------------
# MiniVizデータ送信
# --------------------------------------------------

def send_data(temperature, humidity, pressure, brightness, motion):

    if TOKEN == "your token":
        print("MiniVizトークン未設定")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + TOKEN
    }
    headers = {
    "Content-Type": "application/json"
    }

    # UNIX時間（ミリ秒）
    timestamp_ms = int(time.time() * 1000)

    # 送信データ
    payload = {
        "timestamp": timestamp_ms,
        "label_key": LABEL_KEY,
        "payload": {
            "temperature": temperature,
            "humidity": humidity,
            "pressure": pressure,
            "brightness": brightness,
            "motion": motion
        }
    }

    # 最大4回送信
    for attempt in range(MAX_RETRY + 1):

        response = None

        try:
            print("MiniViz送信:", attempt + 1, "/", MAX_RETRY + 1)

            response = urequests.post(
                URL,
                json=payload,
                headers=headers
            )

            status = response.status_code
            print("HTTP Status:", status)

            # 送信成功
            if 200 <= status < 300:
                print("MiniViz送信成功")
                print("Response:", response.text)
                return True

            # HTTP 429：アクセス制限
            if status == 429:

                retry_after = response.headers.get("Retry-After")

                try:
                    wait = int(retry_after)
                except:
                    wait = 65

                wait = max(1, wait)

                print("HTTP 429: 待機", wait, "秒")

                response.close()
                response = None

                if attempt >= MAX_RETRY:
                    print("再試行上限")
                    return False

                time.sleep(wait)
                continue

            # その他のHTTPエラー
            print("HTTPエラー:", status)

            try:
                print("Response:", response.text)
            except:
                pass

            # 400番台は再送しない
            if 400 <= status < 500:
                print("リクエスト内容を確認してください")
                return False

            # 500番台は再試行
            if attempt < MAX_RETRY:
                print("再試行まで待機:", RETRY_WAIT, "秒")
                response.close()
                response = None
                time.sleep(RETRY_WAIT)
                continue

            return False

        except Exception as e:

            print("通信エラー:", repr(e))

            if attempt >= MAX_RETRY:
                print("送信失敗")
                return False

            print("再試行まで待機:", RETRY_WAIT, "秒")
            time.sleep(RETRY_WAIT)

        finally:
            if response is not None:
                try:
                    response.close()
                except:
                    pass

    return False


# --------------------------------------------------
# 単独実行時のテスト
# --------------------------------------------------

def main():

    print("")
    print("================================")
    print("MiniViz データ送信テスト")
    print("================================")

    print("Project ID:", PROJECT_ID)
    print("Label Key:", LABEL_KEY)

    wifi_connect.connect()

    while True:
        try:
            # センサー読み取り
            # temp, humid, pressure, brightness, motion, switch = (read_sensors())
            temp, humid, pressure, brightness, motion = 25.1 + random.randint(1, 5),40 + random.randint(1, 30),999+ random.randint(1, 30),50 + random.randint(1, 30),random.randint(1, 10)
            print(temp, humid, pressure,brightness, motion)

            wifi_connect.keep_alive()

            start_time = time.time()
            result = send_data(temp, humid, pressure, brightness, motion)
            elapsed_time = time.time() - start_time

            print("今回の送信:", "OK" if result else "NG")
            print("処理時間: {:.4f} 秒".format(elapsed_time))

        except Exception as e:
            print("処理エラー:", e)
# --------------------------------------------------
# プログラム開始
# --------------------------------------------------

if __name__ == "__main__":
    main()

