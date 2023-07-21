"""
2023/05/10
2023/05/21	OLED 焼き付け防止
v1.0
"""
import time
from machine import Pin, I2C
import ssd1306
import config
import random


def OLED(temp,humdy,press):
    try:
        i2c_no,SDA_pin = config.i2c_ini()
        # I2Cバスを設定
        i2c = I2C(i2c_no, sda=Pin(SDA_pin) ,scl=Pin(SDA_pin+1))
        # OLEDディスプレイの設定
        try:
            oled = ssd1306.SSD1306_I2C(128, 32, i2c)
        except:
            pass

        # OLEDディスプレイをクリア
        oled.fill(0)
        
        sp = ' '
        if temp < 10 :sp = sp + ' '
        temp_s  = 'temp  =  ' + sp + str(temp) 

        if humdy  != 100:
            if humdy < 10:
                humdy_s = 'humdy =    ' + str(humdy)
            else:
                humdy_s = 'humdy =   '  + str(humdy)
        else:
                humdy_s = 'humdy =  100.0 '
        
        sp = ''
        if press < 1000:sp = ' '
        press_s = 'press = ' + sp  + str(press)

        if press != 0:
            # 液晶焼き付け防止のため表示位置をずらす
            set_x = random.randint(0,17)
            set_y = random.randint(0, 1)
            set_z = random.randint(0, 1)
            # テキストを描画
            oled.text(temp_s,  set_x, set_y + 0   + set_z)
            oled.text(humdy_s, set_x, set_y + 12  - set_z)
            oled.text(press_s, set_x, set_y + 24  - set_z *2)
        else:
            oled.text('program start!!',  5, 12)

        # 変更を表示
        oled.show()
    except:
        pass   

def OLED_mes(mes):
    try:
        i2c_no,SDA_pin = config.i2c_ini()
        # I2Cバスを設定
        i2c = I2C(i2c_no, sda=Pin(SDA_pin) ,scl=Pin(SDA_pin+1))
        # OLEDディスプレイの設定
        try:
            oled = ssd1306.SSD1306_I2C(128, 32, i2c)
        except:
            pass
        # OLEDディスプレイをクリア
        oled.fill(0)
        # メッセージを書き込み
        oled.text(mes,  5, 12)
        # 変更を表示
        oled.show()
    except:
        pass


def main():
    temp,humdy,press = 24.8,13.9,1323.5
    OLED(temp,humdy,press)
    time.sleep(3)
    OLED_mes("test")
    time.sleep(3)
    OLED_mes("")

if __name__=='__main__':
    main()
