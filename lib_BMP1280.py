"""
20230817    pico用にBMP180 と BMP280 を意識せずに使えるようにしたい。
            まずi2cのディバイス確認をして、プログラムを切り替える         
"""
import time
import i2c_BMP2
import lib_BMP180
import lib_BMP280

def BMP():
    # i2cディバイスを確認
    BMPsesorName = i2c_BMP2.BMP_sensor2()

    if BMPsesorName == 'BMP180' :
        try:
            temp,press1 = lib_BMP180.BMP180(1)
            time.sleep(1)
        except:
            time.sleep(3)
            try:
                temp,press1 = lib_BMP180.BMP180(1)
            except:
                temp,press1 = None,None
        return temp,press1
    

    if BMPsesorName == 'BMP280' :
        try:
            temp,press1 = lib_BMP280.bmp280_dataRead()
            time.sleep(1)
        except:
            time.sleep(3)
            try:
                temp,press1 = lib_BMP280.bmp280_dataRead()
            except:
                temp,press1 = None,None
        press1 = int((press1+0.05)*10)/10
        return temp,press1
    
    print("デバイス取得エラー")
    return 0,0

    
def main():
    print(BMP())

if __name__ == '__main__':
    main()
