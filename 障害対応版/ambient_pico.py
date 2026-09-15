"""
2026/08/29
ambientでのエラーポイントの保存とリカバリーを実施
追加
finally ブロックによるソケットの確実なクローズ
具体的な例外メッセージ（e）のログ記録
s.read() による無制限待機の防止
err_stamp でのファイルオープンエラー対策

"""
import usocket
import ujson
import network
import time
import utime


def err_stamp(mes):
    # JSTに直す（日本はUTC+9）
    t = utime.time() + 9 * 60 * 60
    tm = utime.localtime(t)
    # 日時を文字列に整形
    date_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d} {}".format(
        tm[0], tm[1], tm[2], tm[3], tm[4], tm[5], mes
    )
    print("現在日時TS:", date_str)
    
    # ===== ファイルに保存（エラーガード付き） =====
    try:
        with open("err_stamp.txt", "a") as f:
            f.write(date_str + "\n")
    except Exception as e:
        print("ファイル保存エラー:", e)


# --- Wi-Fi 自動復帰 ---
def wifi_reconnect(ssid, password, timeout=10):
    wlan = network.WLAN(network.STA_IF)
    if not wlan.active():
        wlan.active(True)
    # すでに接続済みなら即OK
    if wlan.isconnected():
        return True
    wlan.connect(ssid, password)
    for _ in range(timeout):
        if wlan.isconnected():
            return True
        time.sleep(1)
    err_stamp("Wi-Fi reconnect failed")
    return False


class AmbientPico:
    def __init__(self, channelId, writeKey, timeout=5):
        self.channelId = channelId
        self.writeKey = writeKey
        self.timeout = timeout
        self.host = "ambidata.io"
        self.path = "/api/v2/channels/{}/dataarray".format(channelId)
        self.lastsend = 0

    # --- DNS 解決（リトライ付き） ---
    def resolve(self):
        for _ in range(3):
            try:
                return usocket.getaddrinfo(self.host, 80)[0][-1]
            except Exception as e:
                time.sleep(1)
                err_stamp(f"DNS err: {e}")
        return None

    # --- Ambient 送信 ---
    def send(self, data):
        # 1. Ambient の 5 秒ルール
        now = time.ticks_ms()
        if self.lastsend != 0 and time.ticks_diff(now, self.lastsend) < 5000:
            err_stamp("time out 403：アクセス頻度制限（5秒以内）")
            return 403

        # 2. JSON payload
        payload = ujson.dumps({
            "writeKey": self.writeKey,
            "data": [data]
        })

        # 3. DNS解決
        addr = self.resolve()
        if addr is None:
            err_stamp("DNS err 500：サーバーアドレス取得失敗")
            return 500

        # 4. ソケット通信
        s = None
        socket_no = 0
        res = None
        
        try:
            s = usocket.socket()
            socket_no = 1
            s.settimeout(self.timeout)
            socket_no = 2
            s.connect(addr)
            socket_no = 3
            
            # HTTP リクエスト作成
            req = (
                "POST {} HTTP/1.1\r\n"
                "Host: {}\r\n"
                "Content-Type: application/json\r\n"
                "Content-Length: {}\r\n"
                "Connection: close\r\n\r\n"
            ).format(self.path, self.host, len(payload))
            
            socket_no = 4
            s.write(req.encode('utf-8'))
            socket_no = 5
            s.write(payload.encode('utf-8'))
            socket_no = 6
            
            # read() の代わりに recv() で安全にレスポンス受信
            res = s.recv(256)
            socket_no = 7

        except Exception as e:
            # 具体的な例外メッセージをログに残す
            err_stamp(f"通信エラー 500 (Step {socket_no}): {e}")
            return 500
        finally:
            # 成功・失敗に関わらず必ずソケットを閉じる
            if s:
                try:
                    s.close()
                except:
                    pass

        # 5. ステータスコード判定
        if res and b"200" in res:
            self.lastsend = now
            return 200
        
        err_stamp(f"サーバー応答エラー 500: レスポンス不鮮明 ({res})")
        return 500