# -*- coding: utf-8 -*-
#!/usr/bin/python3
"""
ID PASS LINE_token
2023/5/7    lib化
2023/5/20   名称をconfig.pyとする
            測定周期を追加
2023/6/10   wifi 使用/不使用を追加
2023/6/19   補正値を持つ
v1.0
"""
def wifi_set():
    return 1 # wifi使用しない時は0

def ID_PASS():
    # wifiのssidとパスワード
    #  ソーズ
    ssid        = 'TKJ'
    password    = '19601121'
    # izumo
    #ssid        = 'snow4'
    #password    = '0728244490'
    return ssid,password

def hosei():
    # センサーのオフセット誤差を補正する補正値です。
    temp  = 0
    humdi = 0
    press = 0
    return temp,humdi,press

def ambi():
    # ambientのチャンネルIDとライトキーを設定
    #  ソーズ
    ch_ID,write_KEY = 64371,"64fd1b3081c33a79"
    # izumo
    ch_ID,write_KEY = 52618,"644c8298f2d4a1e4"
    return ch_ID,write_KEY 

def i2c_ini():
    # センサーとOLEDのi2cチャンネルとSDAのピン番号を設定
    i2c_no = 0
    SDA_pin= 0
    return i2c_no,SDA_pin

def measu_cycle():
    # 1分単位で計測周期を設定
    return 1

def Cds_ini():
    # Cdsで使うアナログ入力pinを設定
    # Cds値の範囲設定
    Cds_max = 60000
    Cds_min = 1500
    return 28,Cds_max,Cds_min


def main():
    print(wifi_set())
    print(ID_PASS())
    print(hosei())
    print(ambi())
    print(i2c_ini())
    print(measu_cycle())
    print(Cds_ini())

if __name__=='__main__':
    main()