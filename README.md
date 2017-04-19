# About

- http://cal.syoboi.jp/ からスクレイピングします。
	- MySQL と連携することで、データベースへのインサート処理をします。
	- twitter アクセストークンがあれば、tweepy を使用し自動ツイートすることができます。
	- アニメタイトルで yahoo 画像検索を行い、自動で一番上の画像をダウンロードしてきます。

# Environment

- macOS 10.12.3
- Python 3.5.2
	- beautifulsoup4 (4.5.3)
	- requests (2.13.0)
	- tweepy (3.5.0)
	- Mastodon.py (1.0.6)

# MEMO

- anime_db.sql 使用時は事前にデータベースの再作成を行う。(DROP DATABASE anime; CREATE DATABASE anime;) 
	- 以下のコマンドで anime データベースにテーブルを自動で作成

```
mysql -uroot -p anime < anime_db.sql
```

- Mastodon.py の内容の修正
	- 579 行目
		- 旧: return self.__api_request('POST', '/api/v1/media', files = {'file': media_file_description}) 
		- 新: return self.__api_request("POST", "/api/v1/media", files = {"file" : (file_name, open(media_file, "rb"))})

- pip でインストールする

```
pip install git+https://github.com/ShotaKitazawa/anitimetable
```

- 使用例

```
import anitimetable
import datetime
import MySQLdb
from mastodon import *


def main():
    broadcaster_list = [
        "NHK Eテレ",
        "日本テレビ",
        "テレビ朝日",
        "TBS",
        "テレビ東京",
        "フジテレビ",
        "TOKYO MX",
        "AT-X",
    ]
    auth_list = {
        "CONSUMER_KEY":"8K6BcNqg1OHPh2t2CZLOlxuDb",
        "CONSUMER_SECRET":"S4W13zYtG6GjH7xzaSQlVbUgx4h0sNVAkWPBUIZBdnsICQ7h02",
        "ACCESS_TOKEN":"830059724624125952-faRkknQmBtleYPfV8XjeOS3aiLLFmI8",
        "ACCESS_TOKEN_SECRET":"COv4C7HiUda1JltjvYus4ePhDXzKrpWKhQ8o6XYVrZK4k",
    }
    mastodon = Mastodon(
        client_id="yourapp_clientcred.txt",
        access_token="your_usercred.txt",
        api_base_url="https://mstdn.jp",
    )
    CONNECTION = MySQLdb.connect(
        user="root",
        passwd="F4p3DEbQ",
        host="localhost",
        db="anime",
    )
    titlelist_id = [
        "1",  # 放送中アニメ
        # "2", # ラジオ
        # "3", # ドラマ
        # "4", # 特撮
        # "5", # アニメ関連
        # "7", # OVA
        # "8", # 映画
         "10", # 放送終了アニメ
    ]
		# 初期化
    now = datetime.datetime.now()
    Today_timetable = anitimetable.AniTimeTable(now, broadcaster_list, DB_CONNECTION=CONNECTION)

	# 今日放送するアニメを全て表示する。
    #Today_timetable.show_all()

	# 現在放送中のアニメを表示する
	## tweet 引数を取ることでツイートすることが出来る。
	## toot 引数を取ることでトゥートすることが出来る。
    #Today_timetable.now_program()
    #Today_timetable.now_program(mode="tweet", auth_data=auth_list)
    #Today_timetable.now_program(mode="toot", auth_data=mastodon)

	# titlelist_id に対応したデータを取ってくる
	## DB への insert と 画像ファイルのダウンロードを行う
    #Today_timetable.insert_db(titlelist_id)

	# 5 分おきにツイート(常駐)
	## 引数: [0,0] > 現在放送中のアニメ, [0,29] > 0 時間 29 分後放送のアニメ
    #Today_timetable.auto_tweet([0,0],[0,29])


if __name__ == "__main__":
    main()
```

# TODO

- 完: tweet に第何話かの情報を付ける > つけた

- 完:  今季放送開始でないアニメのイメージファイルがどこにあるかがわからない > 時期でフォルダ分けするのをやめる
	- 番組ID,番組名,番組イメージのpath のテーブルを作る。

- 完: insertdb.py を AniTimeTable のモジュール化 > insert_db 関数つくった

- 完: しょぼいカレンダー と あにぽた でアニメのタイトルが違うと困る。 > 全部しょぼいカレンダーで完結させる
	- 優先度高
	- しょぼいカレンダー からデータベースにinsertする情報も取ってくる
		- 画像は [title] で google 画像検索して一番上の画像とか？
			- yahoo 検索
		- anime_db.sql の見直し

- 歌手名がキャラクター名であっても、その名前で DB に insert してしまう。
	- あきらめモード

- html 自動生成
	- Django?
	- ooからxxを検索するとか？
		- 例: アニメタイトルから、そのアニメのOP/EDの歌手名を検索

- 完: xx分前のアニメをリストアップするメソッドの作成
	- now_program メソッドを真似すればかんたん

- 完: insert_db 関数の titlelist_id を利用者側から選択できるようにする。

- 画像検索 & ダウンロード するモジュールを別の一つの関数にする。

- (おそらく) auto_tweet メソッドの引数に ([0,0], [0,15]) とか取ると、放送中&15分後も放送中が両方の条件に引っかがってダサい
	- ってか 2 回ツイートする

- DB やばい
	- op テーブルの singer_id カラムおかしい
		- 歌手が2人以上のときも singer_id に一人しか入ってない
		- op テーブルの主キーを op_id & singer_id にすればよさげ
	- anime_broadcaster テーブル出来てない

- Mastodon に対応
	- 写真付きトゥートができない

- n時間前アニメができてない？
	- 分指定はできる
