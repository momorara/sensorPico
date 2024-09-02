#!/bin/env python3

"""
LINEにトークンを使ってメッセージを送ります。

2024/09/02 picoでのLINE送信

lib_LINE.py
"""
import urequests

def send_LINE(message):
    # LINE Notifyのトークン
    token = 'YOUR_LINE_NOTIFY_TOKEN'
    
    # LINE NotifyのAPI URL
    url = 'https://notify-api.line.me/api/notify'
    # ヘッダーにトークンを含める
    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    # POSTリクエストを送信
    response = urequests.post(url, headers=headers, data='message=' + message)
    # レスポンスの確認
    print(response.text)

def main():
    send_LINE("test123")

if __name__=='__main__':
    main()
