# -*- coding: utf-8 -*-
#!/usr/bin/python3
"""
2023/5/4
wifiのon-offを行う
osはいないので、やってくれないよ!!
2023/5/7    lib化
2023/05/20  設定ファィルをconfig.pyとした
2023/06/11  ip_addressを返す
v1.0
"""
import urequests as requests
import network
import utime
import config
import machine

def wifi_onoff(mode):
    if mode == 'on':
        # wifiの電源を入れる
        machine.Pin(23, machine.Pin.OUT).high()
        #自宅Wi-FiのSSIDとパスワードを入力
        ssid,password = config.ID_PASS()

        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(ssid, password)

        # Wait for connect or fail
        max_wait = 10
        while max_wait > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            max_wait -= 1
            print('waiting for connection...')
            utime.sleep(1)
        status = wlan.ifconfig()
        # print( 'ip = ' + status[0] )
        return status[0]
    else:
        # wifiの電源を切る
        machine.Pin(23, machine.Pin.OUT).low()
    

def main():
    print("ip:",wifi_onoff('on'))

if __name__=='__main__':
    main()
