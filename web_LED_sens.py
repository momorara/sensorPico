"""
2023/06/16  PicoWでwebサーバーを立てて、webでボタンを押すと
            サンプルプログラムであり、セキュリティ、障害耐性など考慮されていません。
    01      picoのLEDが点灯、消灯します。
            thonnyに繋いだ状態で動作させてstopした後は、再接続してださい。
            多分ソケットのエラーを回復するのに30秒だかかかるっぽい
2023/06/17  ボタンを横に並べて、大きく。endボタン追加
v1.0
"""
import machine
import socket
import time
import network
import sys

import config
import SSD1306
import lib_BMP180
import lib_AHT10

# エラーが2回続けば、データ欠損として、Noneとする。
def keisoku():
    try:
        temp1,humi1 = lib_AHT10.aht10(1)
    except:
        time.sleep(1)
        try:
            temp1,humi1 = lib_AHT10.aht10(1)
        except:
            temp1,humi1 = None,None
    try:
        temp,press1 = lib_BMP180.BMP180(1)
    except:
        time.sleep(1)
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

# GPIOピンの設定
led1 = machine.Pin(16, machine.Pin.OUT)
led2 = machine.Pin(17, machine.Pin.OUT)

led1.on()
time.sleep(2)
led1.off()
led2.on()
time.sleep(2)
led2.off()

# HTMLページの設定
html = """<!DOCTYPE html>
<html>
    <head> 
        <title>RaspberryPi Pico LED Control</title> 
        <style>
            .button {{
                font-size: 20px;
                padding: 10px 24px;
                margin: 24px 2px;  /* ボタン間のスペースを広げる */
                display: inline-block;
                border: none;
                color: black;  /* テキスト色を黒に設定 */
                text-align: center;
                text-decoration: none;
                transition-duration: 0.4s;
                cursor: pointer;
                border-radius: 12px;
                box-shadow: 0 9px #999;
            }}
            .button:active {{
                box-shadow: 0 5px #666;
                transform: translateY(4px);
            }}
            .button1 {{
                background-color: #4CAF50;
            }}
            .button2 {{
                background-color: #008CBA;
            }}
            .button3 {{
                background-color: #f44336;
            }}
            .button4 {{
                background-color: #e7e7e7; 
                color: black; 
            }}
            .reading {{
                font-size: 30px;  /* テキストサイズを大きく設定 */
            }}
        </style>
    </head>
    <body> 
        <h1>RaspberryPi Pico LED Control and Sensor</h1> 
        <form method="POST">
            <button class="button" name="led" value="ON1">LED1 ON</button>
            <button class="button" name="led" value="OFF1">LED1 OFF</button>
            <button class="button" name="led" value="ON2">LED2 ON</button>
            <button class="button" name="led" value="OFF2">LED2 OFF</button><br/>
            <button class="button" name="led" value="BLINK">BLINK</button>
            <button class="button" name="led" value="END">END</button>
        </form>
        <p style="font-size: 30px;">Temperature: {temp} C</p>
        <p style="font-size: 30px;">Humidity   : {humi} %</p>
        <p style="font-size: 30px;">Pressure   : {press} hPa</p>
    </body>
</html>
"""
def web_page(temp, humi, press):
  return html.format(temp=temp, humi=humi, press=press)
# def web_page():
#     return html

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)

while True:
    conn, addr = s.accept()
    request = conn.recv(1024)
    request = str(request)
    led_on1 = request.find('led=ON1')
    led_off1 = request.find('led=OFF1')
    led_on2 = request.find('led=ON2')
    led_off2 = request.find('led=OFF2')
    led_blink = request.find('led=BLINK')
    led_end = request.find('led=END')

    #print(led_on1,led_off1,led_on2,led_off2)
    # センサからデータを読み取る
    temp, humi, press = read_sensor()

    if led_end > 6:
        print('LED1 END')
        led1.off()
        led2.off()
        conn.close()
        sys.exit()

    if led_on1 > 6:
        print('LED1 ON')
        led1.on()
    if led_off1 > 6:
        print('LED1 OFF')
        led1.off()
    if led_on2 > 6:
        print('LED2 ON')
        led2.on()
    if led_off2 > 6:
        print('LED2 OFF')
        led2.off()
    if led_blink > 6:
        print('LED BLINK')
        for i in range(5):
            led1.on()
            time.sleep(0.5)
            led1.off()
            led2.on()
            time.sleep(0.5)
            led2.off()
            led2.off()
    response = web_page(temp, humi, press)
    conn.send('HTTP/1.1 200 OK\n')
    conn.send('Content-Type: text/html\n')
    conn.send('Connection: close\n\n')
    conn.sendall(response)
    conn.close()
