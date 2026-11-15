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
2024/09/08  mail追加 2
2026/11/14  sensorPicoとmimamoriPicoのなるべく共通化
            メール送信を削除
"""
def wifi_set():
    return 1 # wifi使用しない時は0

def ID_PASS():
    # wifiのssidとパスワード
    # あなたのwifiの設定に変更してください。
    ssid        = 'your ssid'
    password    = 'your password'
    return ssid,password

# sensorPicoとmimamoriPicoのセンサーの有無を設定
def BMP_SR602():
    # BMPの有:１ 無:0
    BMP = 1
    # SR602の有:１ 無:0
    SR602 = 0
    return BMP,SR602

def hosei():
    # センサーのオフセット誤差を補正する補正値です。
    temp  = 0
    humdi = 0
    press = 0
    return temp,humdi,press

def BLYNK_token():
    BLYNK_AUTH = "your token"
    # your tokenの場合は、送信しない
    return BLYNK_AUTH

def MINIVIZ_token():
    MINIVIZ_AUTH = "your token"
    ROJECT_ID    = "your ID"
    LABEL_KEY    = "your Key"
    return MINIVIZ_AUTH,ROJECT_ID,LABEL_KEY

def i2c_ini():
    # センサーとOLEDのi2cチャンネルとSDAのピン番号を設定
    i2c_no = 0
    SDA_pin= 0
    return i2c_no,SDA_pin

def measu_cycle():
    # 2分単位で計測周期を設定
    return 2

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
    print(i2c_ini())
    print(measu_cycle())
    print(Cds_ini())

if __name__=='__main__':
    main()
