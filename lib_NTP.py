# -*- coding: utf-8 -*-
#!/usr/bin/python3
"""
2023/05/21  NTPにて時刻あわせ
v1.0
"""

def NTP_set():
    import network
    import time
    import ntptime
    #日時取得
    ntptime.settime()
    UTC_OFFSET = 9 * 60 * 60
    loacal_date_time = time.localtime(time.time() + UTC_OFFSET)
    print(loacal_date_time)

# テストするのにLINEを送るなどする必要があるので、省きます。