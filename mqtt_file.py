# 2024/8/22

# mtqq_topic_no.txtを作るなりしてtopicを取得する

# Ambientの後に以下を行う
# ・ambientが成功したことを持ってネット接続出来ていることとする
# ・mtqq_topic_no.txtがあるか確認

def topic_get():
    file_name = "mtqq_topic_no.txt"
    topic     = "tkj/raspberry_pico/temp_AHT/" 
    glaph_n   = 47
    try:
        with open(file_name): # あれば、その数字をmtqq_topic_noとする
            print(f"{file_name} は存在します。")
            # ファイルを読み取りモードで開く
            with open(file_name, "r") as file:
                # ファイルの内容をすべて読み取る
                mtqq_topic_no = file.read()
            mtqq_topic_no= int(mtqq_topic_no)
            # 読み取った内容を表示
            print(mtqq_topic_no)

    except:# なければ作り、ランダムな数字を保存
        print(f"{file_name} は存在しません。")
        import random
        # 1からglaph_nまでの乱数を生成
        mtqq_topic_no = random.randint(1, glaph_n)
        print(mtqq_topic_no)
        with open(file_name, "w") as file:
            # ファイルに文字を書き込む
            file.write(str(mtqq_topic_no) + "\n")

    # 　　数字はダッシュボードのグラフの数　1からglaph_nの 整数
    # 　　その数字をmtqq_topic_noとする
    if mtqq_topic_no != 0: # ・mtqq_topic_noが 0 なら何もせず終了
        # ・mtqq_topic_noが 1-n なら温度情報をその番号でpublishする
        topic = topic + str(mtqq_topic_no)
    #print(topic)
    return topic

# * mtqq_topic_no.txtを手動で編集することで
# 　ファィルを削除　新しいランダムな番号とできる
# 　0を書き込むことで、動作しないようにできる
# 　任意の 0-n の数字を書き込むことで、任意のグラフに表示できる

# トピックは
#  tkj/raspberry_pico/temp_AHTx0/00xx
# とか

def main():
    topic = topic_get()
    print(topic)

if __name__=='__main__':
    main()

