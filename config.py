# -*- coding: utf-8 -*-
#!/usr/bin/python3
"""
ID PASS LINE_token
2023/5/7    lib化
2023/5/20   名称をconfig.pyとする
            測定周期を追加
"""

def ID_PASS():
    # wifiのssidとパスワード
    ssid        = 'snow4'
    password    = '0728244490'
    # ssid        = 'TKJ'
    # password    = '19601121'
    return ssid,password

def LINE_token():
    # LINEのトークン設定
    return '4N4RSrOxn8LRTl9VQBag8J2QwTIXbLoZrmRsG14PH8Q'

def mqtt_broker():
    # mqttのプローかー名を設定
    return 'broker.emqx.io'

def ambi():
    # ambientのチャンネルIDとライトキーを設定
    #  ソーズ
    ch_ID,write_KEY = 64371,"64fd1b3081c33a79"
    # izumo
    ch_ID,write_KEY = 52618,"644c8298f2d4a1e4"
    return ch_ID,write_KEY 

def i2c_ini():
    # センサーとOLEDのi2cチャンネルとSDAのピン番号を設定
    i2c_no = 1
    SDA_pin= 14 
    return i2c_no,SDA_pin

def measu_cycle():
    # 1分単位で計測周期を設定
    return 1

def Cds_ini():
    # Cdsで使うアナログ入力pinを設定
    # Cds値の範囲設定
    Cds_max = 60000
    Cds_min = 1500
    return 26,Cds_max,Cds_min


def main():
    print(ID_PASS())
    print(LINE_token())
    print(mqtt_broker())
    print(ambi())
    print(i2c_ini())
    print(measu_cycle())
    print(Cds_ini())

if __name__=='__main__':
    main()