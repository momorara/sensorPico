# 2024/8/22
"""
トピックとデータを引数にmqtt_sendを実行すると
指定されたプローカーに対にしてパブリッシュします。
2024/08/24  mqttのコアプログラムの名前を変え、インストールしやすいようにした
"""
import network
import time
import ubinascii
#from machine import Pin
import machine
# from umqtt.simple import MQTTClient
# 同一階層にコピーするだけでよくするのと、わかりやすい名前とした
from lib_mqtt import MQTTClient

# # Wi-Fi接続情報
# wifi接続できているものとする

# MQTTブローカー情報
broker = 'broker.emqx.io'
client_id = ubinascii.hexlify(machine.unique_id())
print(client_id)

# Wi-Fiに接続
def connect_wifi():
    return
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    while not wlan.isconnected():
        print('Wi-Fiに接続中...')
        time.sleep(1)
    print('Wi-Fiに接続完了:', wlan.ifconfig())

# MQTT接続
def connect_mqtt():
    client = MQTTClient(client_id, broker)
    client.connect()
    print('MQTTに接続完了')
    return client

# メインプログラム
def mqtt_send(topic,data):
    print(topic,data)
    connect_wifi()
    client = connect_mqtt()
    try:
        # メッセージの送信
        client.publish(topic, str(data))
        print(f"メッセージ '{data}' をトピック '{topic}' に送信しました")
    finally:
        client.disconnect()
        print('MQTT接続を終了しました')

def main():
    topic = "tkj/raspberry_pico/temp_AHT/1"
    data = 31
    mqtt_send(topic,data)

if __name__ == '__main__':
    main()

