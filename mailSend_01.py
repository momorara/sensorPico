import time
from ubinascii import b2a_base64
import network
import socket
import ssl

import config
import lib_LED

#http://zattouka.net/GarageHouse/micon/ESP/ESP-WROOM-02/ESP8266_Mail.htm
# http://zattouka.net/GarageHouse/index.htm
# HP下部にオープンドメインとの記述あり

# subjectには日本語はだめ
# 本文は日本語が通るみたい


# config_Mailで設定情報を書き換える
# MailServerName =  # メールサーバー名
# FromName       =  # メールの送信者
# ToName         =  # メールの送り先
# UserName       =  # プロバイダーのアカウント(ユーザー名)
# UserPass       =  # プロバイダーのパスワード

# wifiセッティングの取得
ESSID,Password= config.ID_PASS()
print(ESSID,Password)

# mailセッティングの取得
mail_onoff,MailServerName,UserName,UserPass,toMailAddres,mail_title,mail_body = config.mail_setting()
print(mail_onoff,MailServerName,UserName,UserPass,toMailAddres,mail_title,mail_body)
FromName = UserName

# メールコマンドの発行を行う
def MsgCMD(sdt,soc):
    _s = '%s\r\n' % sdt
    soc.write(_s)
    print(_s, end='')
    _s = soc.readline()
    print(_s)
    if int(_s.decode()[0:3]) < 400:
        return True
    else:
        return False

# 認証コマンドの発行を行う
def AUTHCMD(sdt,soc):
    _s = '%s\r\n' % sdt
    soc.write(_s)
    print(_s, end='')
    while True:
        _s = soc.readline()
        print(_s)
        if _s[0:3] == b'334' or _s[0:3] == b'235':
            _ans = True
            break
        if _s[0:3] == b'500' or not _s:
            _ans = False
            break
    return _ans


def mailSend(mail_subject,mail_body,toMailAddres):

    # Wi-Fi 接続を設定する為にクライアントオブジェクトのインターフェースを作成する
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        sta_if.active(True)
        sta_if.connect(ESSID, Password)  # ステーションインターフェイスを有効にする
        while not sta_if.isconnected():  # WiFiネットワークに接続する
            pass
    print('\r\n[network config]\r\n', sta_if.ifconfig())

    # 指定されたアドレスファミリ、ソケットタイプ、プロトコル番号を使い、新しいソケットを作成する
    addr = socket.getaddrinfo(MailServerName, 465)[0][-1]
    soc = socket.socket()
    soc.connect(addr)           # メールサーバーに接続
    print('listening on', addr)
    soc = ssl.wrap_socket(soc)  # SSL通信

    while True:
        # 応答を待つ
        bMsg = soc.readline()
        print(bMsg)
        # SMTP認証
        AUTHCMD('AUTH LOGIN',soc)
        s = b2a_base64(UserName).decode()   # BASE64に変換、bytes型オブジェクトで返る
        AUTHCMD(s[0:len(s)-1],soc)              # データ後ろの改行文字を省く(例:b'UGFzc3dv\n')
        s = b2a_base64(UserPass).decode()
        ans = AUTHCMD(s[0:len(s)-1],soc)
        if not ans: break
        # 送信者
        ans = MsgCMD('MAIL FROM: ' + FromName,soc)
        if not ans: break
        # 送り先
        ans = MsgCMD('RCPT TO: '   + toMailAddres,soc)
        if not ans: break
        # メールデータ
        ans = MsgCMD('DATA',soc)
        if not ans: break
        # データのヘッダ
        soc.write('To: '      + toMailAddres + '\r\n')
        soc.write('From: '    + FromName     + '\r\n')
        soc.write('Subject: ' + mail_subject + '\r\n\r\n')
        # データの本文
        soc.write(mail_body + '\r\n')
        ans = MsgCMD('.',soc)
        if not ans: break
        # メール終了
        soc.write('QUIT\r\n')
        break

    # ソケットを閉じる
    soc.close()
    # アクセスポイントインターフェイスを無効にする
    sta_if.active(False)


def main():
    lib_LED.LEDonoff()

    mail_subject = "testMail"   # 全角文字はメーラーにより文字化けする
    mail_body    = "test test"  # 全角文字もOK
    toMailAddres = "pc_mailbox@mineo.jp"
    mailSend(mail_subject,mail_body,toMailAddres)

    lib_LED.LEDonoff()

if __name__=='__main__':
    main()
