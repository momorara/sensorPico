import network
import time
import urequests
import random
import config
import wifi_connect
import lib_NTP

# Blynk Auth Token
BLYNK_AUTH = config.BLYNK_token()

# 設定
SEND_INTERVAL = 60
MAX_RETRY = 3
RETRY_WAIT = 2


# Blynkへ6項目を一括送信
def send_data(temp, humid, pressure, brightness, motion):
    if BLYNK_AUTH == "your token":
        return

    url = (
        "https://blynk.cloud/external/api/batch/update"
        "?token=" + BLYNK_AUTH
        + "&V20=" + str(temp)
        + "&V21=" + str(humid)
        + "&V22=" + str(pressure)
        + "&V23=" + str(brightness)
        + "&V24=" + str(motion))

    for attempt in range(1, MAX_RETRY + 1):
        # # Wi-Fiが切れていたら再接続
        # if not connect_wifi():
        #     print("Wi-Fi接続失敗:", attempt)
        #     time.sleep(RETRY_WAIT)
        #     continue
        response = None
        try:
            response = urequests.get(url)
            if response.status_code == 200:
                print("Blynk一括送信成功")
                return True
            print("HTTPエラー:", response.status_code)
            try:
                print(response.text)
            except Exception:
                pass
        except Exception as e:
            print("Blynk通信エラー:", e)
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
        if attempt < MAX_RETRY:
            time.sleep(RETRY_WAIT)

    print("Blynk一括送信失敗")
    return False


def main():
    wifi_connect.connect()
    lib_NTP.NTP_set()
    # メインループ
    while True:
        try:
            # 次の正分まで待つ
            now = time.localtime()
            wait_sec = 60 - now[5]
            print("次の正分まで待つ",wait_sec,"秒")
            time.sleep(wait_sec)

            # 毎正分に送信処理を開始
            print("送信開始:", time.localtime())

            # センサー読み取り
            # temp, humid, pressure, brightness, motion, switch = (read_sensors())
            temp, humid, pressure, brightness, motion = 25.1 + random.randint(1, 5),40 + random.randint(1, 30),999+ random.randint(1, 30),50 + random.randint(1, 30),random.randint(1, 10)
            print(temp, humid, pressure,brightness, motion)

            wifi_connect.keep_alive()

            start_time = time.time()
            # Blynkへ送信
            send_data(temp, humid, pressure,brightness, motion)
            elapsed_time = time.time() - start_time

            print("処理時間: {:.4f} 秒".format(elapsed_time))

        except Exception as e:
            print("処理エラー:", e)


if __name__=='__main__':
    main()
