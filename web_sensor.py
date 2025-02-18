"""
2023/06/15  PicoWでwebサーバーを立てて、気温、湿度、気圧を表示します。
    01      サンプルプログラムであり、セキュリティ、障害耐性など考慮されていません。
            thonnyに繋いだ状態で動作させてstopした後は、再接続してださい。
            多分ソケットのエラーを回復するのに30秒だかかかるっぽい
            NTP入れる
            スタンドアローンで動くか　ok
            OLED対応　ip表示
"""

import socket
import network
import config
import time
import machine

import lib_BMP180
import lib_AHT10
import SSD1306
import lib_NTP


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
        temp,press1 = lib_BMP180.BMP180(1)
        time.sleep(1)
    except:
        time.sleep(3)
        try:
            temp,press1 = lib_BMP180.BMP180(1)
        except:
            temp,press1 = None,None
    return press1,temp1,humi1

# センサからデータを読み取る関数（具体的なセンサに合わせて修正が必要）
def read_sensor():
    # センサー測定
    press,temp,humi = keisoku()
    return temp, humi, press

# wifi設定値取得
SSID,PASSWORD = config.ID_PASS()
# ネットワーク設定
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect(SSID, PASSWORD)  # Wi-FiのSSIDとパスワードを入力

# ネットワーク接続を待つ
while not sta_if.isconnected():
    print('Connecting to network...')
    time.sleep(1)
print('connected!')

# OLEDにipアドレス表示
status = sta_if.ifconfig()
print( 'ip = ' + status[0] )
SSD1306.OLED_mes(status[0])

# 時刻合わせ
lib_NTP.NTP_set()


# ソケットの作成
s = socket.socket()
# ソケットのバインド
ai = socket.getaddrinfo('0.0.0.0', 80)
addr = ai[0][-1]
s.bind(addr)

# サーバーの開始
s.listen(5)
print('listening on', addr)

# データのリスト作成
data = []
UTC_OFFSET = 9 * 60 * 60
try:
    while True:
        # クライアントからの接続を待つ
        res = s.accept()
        client_s = res[0]
        client_addr = res[1]
        print('connection from', client_addr)
        
        # HTTPリクエストを受け取る
        request = client_s.recv(1024)
        print('request:', request)
        
        now = time.localtime(time.time() + UTC_OFFSET)
        print("Time",now[3],":",now[4])
        time_now = str(now[3]) + ":" + str(now[4])
        # センサからデータを読み取る
        temperature, humidity, pressure = read_sensor()
        data.append((time_now, temperature, humidity, pressure))
        if len(data) > 30:
            data.pop(0)
        
        # HTTPレスポンスを送信
        response = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'
        response += '<html><head><meta http-equiv="refresh" content="62"></head><body>'
        response += '<table>'
        response += '<tr><th>Time /</th><th>Temp  </th><th>Humi  </th><th>Press  </th></tr>'
        for item in data:
            response += '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(*item)
        response += '</table>'
        response += '</body></html>'
        client_s.send(response)
        
        # ソケットのクローズ
        client_s.close()
except:
    client_s.close()