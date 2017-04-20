import sys
import os
import re
import datetime
import threading
from bs4 import BeautifulSoup
import requests
import tweepy
from mastodon import *


class AniTimeTable:

    URL = "http://cal.syoboi.jp"
    AUTO_TWEET_TIME = 60

    def __init__(self, time, broadcaster_list,  DB_CONNECTION="_"):
        if not isinstance(time, datetime.datetime):
            sys.stderr.write('Error: class initialized error: argment type is not datetime.datetime\n')
            return
        self.time = time
        self.broadcaster = broadcaster_list
        self.connection = DB_CONNECTION
        self.auth_twitter = {"CONSUMER_KEY": "_","CONSUMER_SECRET": "_","ACCESS_TOKEN": "_","ACCESS_TOKEN_SECRET": "_",}
        self.auth_mastodon = "_"

    def show_all(self):
        soup = self._return_soup("/?date=" + self.time.strftime("%Y/%m/%d"))
        programs = soup.find("td", {"class": "v3dayCell v3cellR "}).find_all("div", {"class": "pid-item v3div"})
        for program in programs:
            print(program["title"])

    def insert_db(self, titlelist_id):
        if self.connection == "_":
            sys.stderr.write('> Error: database not initialized')
        for i in titlelist_id:
            soup = self._return_soup("/list?cat={0}".format(i))
            title_list = soup.find("table", {"class": "TitleList TableColor"})
            title_url = title_list.find_all("a")
            for j in title_url:
                title = j.text
                print("== " + title + " ==")
                soup = self._return_soup(j["href"])
                try:
                    staff_list = soup.find_all("table", {"class": "section staff"})
                    if self._check_table(title, "anime"):
                        c = self.connection.cursor()
                        c.execute('insert into anime(name) values("{}")'.format(title))
                        c.close()
                    for staffs in staff_list:
                        staff_data = staffs.find("table", {"class": "data"}).find_all("tr")
                        self._tidpage_section_insert(staff_data, title, [["原作", "writer"], ["監督", "director"], ["制作", "brand"]])

                    op_list = soup.find_all("table", {"class": "section op"})
                    for ops in op_list:
                        op_title_source = ops.find("div", {"class": "title"}).text
                        op_title = re.sub(r"^.*?「(.*)」$", r"\1", op_title_source)
                        op_data = ops.find("table", {"class": "data"}).find_all("tr")
                        self._tidpage_section_insert(op_data, title, [["歌", "op", op_title]])

                    ed_list = soup.find_all("table", {"class": "section ed"})
                    for eds in ed_list:
                        ed_title_source = eds.find("div", {"class": "title"}).text
                        ed_title = re.sub(r"^.*?「(.*)」$", r"\1", ed_title_source)
                        ed_data = eds.find("table", {"class": "data"}).find_all("tr")
                        self._tidpage_section_insert(ed_data, title, [["歌", "ed", ed_title]])
                except Exception as error:
                    print(error)
                finally:
                    self._search_and_download_image(title)

    def now_program(self, time_ago=[0, 0], mode="_", auth_twitter="_", auth_mastodon="_"):
        if mode.lower() == "tweet":
            auth = tweepy.OAuthHandler(auth_twitter["CONSUMER_KEY"], auth_twitter["CONSUMER_SECRET"])
            auth.set_access_token(auth_twitter["ACCESS_TOKEN"], auth_twitter["ACCESS_TOKEN_SECRET"])
            api = tweepy.API(auth)
        elif mode.lower() == "toot":
            mastodon = auth_mastodon

        # TODO: もし %H <=6 ならば %d -= 1
        # TODO: 0 ~ 6 時を 24 ~ 30 時に変換する
        ## DATETIME 型使わないほうがええんちゃう
        if self.time.hour <= 6:
            tmp_time = datetime.datetime(self.time.year, self.time.month, self.time.day - 1, self.time.hour, self.time.minute)
            soup = self._return_soup("/?date=" + tmp_time.strftime("%Y/%m/%d"))
        else:
            soup = self._return_soup("/?date=" + self.time.strftime("%Y/%m/%d"))

        programs = soup.find("td", {"class": "v3dayCell v3cellR "}).find_all("div", {"class": "pid-item v3div"})
        for program in programs:
            if self._time_check(program, time_ago):
                broadcaster_check = self._broadcaster_check(program)
                if broadcaster_check != "_":
                    atime = program["title"]
                    if time_ago[0] == 0 and time_ago[1] == 0:
                        broad_minute = ((self.time - self._broad_time(program, time_ago)[0])).total_seconds() // 60 - 1
                        message = "{}分前から放送中です。".format(int(broad_minute+1))
                    elif time_ago[0] == 0:
                        broad_minute = ((self._broad_time(program, time_ago)[0]) - self.time).total_seconds() // 60
                        message = "放送{}分前です。".format(int(broad_minute))
                    else:
                        broad_time = ((self._broad_time(program, time_ago)[0]) - self.time).total_seconds() // 60
                        broad_hour = broad_time // 60
                        broad_minute = broad_time - broad_hour * 60
                        message = "放送{}時間{}分前です。".format(int(broad_hour), int(broad_minute))
                    ordinal = self._check_ordinal(program)
                    if mode.lower() == "tweet":
                        self._tweet_with_picture(program, broadcaster_check, message, api)
                    elif mode.lower() == "toot":
                        self._toot_with_picture(program, broadcaster_check, message, mastodon)
                    else:
                        title = program.find("a", {"class": "v3title"}).text
                        weekday = self._check_weekday()
                        print(title + "\n" + broadcaster_check + ": " + weekday + " " + atime + "\n" + ordinal + message)
                        print("===")

    def auto_tweet(self, auth_data, *times_ago):
        self.auth_twitter = auth_data
        while(True):
            if datetime.datetime.now().second == 0 and datetime.datetime.now().minute % (self.AUTO_TWEET_TIME/60) == 0:
                break
        t = threading.Thread(None, self._tweet_per_minute, None, times_ago)
        t.start()

    def _tweet_per_minute(self, *times_ago):
        self.time = datetime.datetime.now()
        for i in times_ago:
            self.now_program(time_ago=i, mode="tweet", auth_twitter=self.auth_twitter)
        # 5 分毎にツイートする
        t = threading.Timer(self.AUTO_TWEET_TIME, self._tweet_per_minute, times_ago)
        t.start()

    def auto_toot(self,auth_data, *times_ago):
        self.auth_mastodon = auth_data
        while(True):
            if datetime.datetime.now().second == 0 and datetime.datetime.now().minute % (self.AUTO_TWEET_TIME/60) == 0:
                break
        t = threading.Thread(None, self._toot_per_minute, None, times_ago)
        t.start()

    def _toot_per_minute(self, *times_ago):
        self.time = datetime.datetime.now()
        for i in times_ago:
            self.now_program(time_ago=i, mode="toot", auth_mastodon=self.auth_mastodon)
        # 5 分毎にツイートする
        t = threading.Timer(self.AUTO_TWEET_TIME, self._toot_per_minute, times_ago)
        t.start()

    def _search_and_download_image(self, title):
        c = self.connection.cursor()
        c.execute('select anime_id from anime where name="{0}"'.format(title))
        anime_id = c.fetchall()[0][0]
        c.close()
        response = requests.get("https://search.yahoo.co.jp/image/search?p={0}&ei=UTF-8&rkf=1".format(title))
        if response.status_code == 404:
            sys.stderr.write('> Error: URL page notfound.\n')
            sys.exit(1)
        html = response.text.encode("utf-8", "ignore")
        soup = BeautifulSoup(html, "lxml")
        content = soup.find("div", {"id": "contents"})
        image_url = content.find("img")["src"]
        image = requests.get(image_url)
        with open("{0}/.images/{1}.jpg".format(os.path.expanduser('~'), anime_id), 'wb') as myfile:
            for chunk in image.iter_content(chunk_size=1024):
                myfile.write(chunk)

    def _tidpage_section_insert(self, sections, title, insertlists):
        for i in sections:
            for j in insertlists:
                if re.match("^(.+・|){0}(・.+|)$".format(j[0]), i.find("th").text):
                    # DBへのinsert処理
                    schema = re.sub(r"^(.+・|)({0})(・.+|)$".format(j[0]), r"\2", i.find("th").text)
                    contents = i.find_all("a", {"class": "keyword nobr"})
                    if len(contents) == 0:
                        contents = i.find_all("a", {"class": "keyword"})
                    print(contents)
                    c = self.connection.cursor()
                    for content in contents:
                        if j[1] == "op" or j[1] == "ed":
                            # singer テーブルへの insert
                            if self._check_table(content.text, "singer"):
                                c.execute('insert into singer(name) values ("{0}")'.format(content.text))
                            # singer テーブルから singer_id の抽出
                            c.execute('select singer_id from singer where name="{0}"'.format(content.text))
                            singer_id = c.fetchall()[0][0]
                            # op|ed テーブルへの insert
                            ## TODO: op|ed テーブルは op_id と singer_id が主キーなのに、ある op_id が一つ存在したらそれ以上インサートしないようになっている > 歌一つに歌手一人しか入っていないなう > _check_table メソッドじゃなくて他のアプローチ？
                            if self._check_table(j[2], j[1]):
                                c.execute('insert into {0}(name, singer_id) values ("{1}", {2})'.format(j[1], j[2], singer_id))
                            # op|ed テーブルから op|ed_id の抽出
                            c.execute('select {0}_id from {0} where name="{1}"'.format(j[1], j[2]))
                            content_id = c.fetchall()[0][0]
                        else:
                            # j[1] テーブルへの insert
                            if self._check_table(content.text, j[1]):
                                c.execute('insert into {0}(name) values ("{1}")'.format(j[1], content.text))
                        # j[1] テーブルから "{}_id".format(j[1]) の抽出
                            c.execute('select {0}_id from {0} where name="{1}"'.format(j[1], content.text))
                            content_id = c.fetchall()[0][0]
                        # anime テーブルから anime_id の抽出
                        c.execute('select anime_id from anime where name="{0}"'.format(title))
                        anime_id = c.fetchall()[0][0]
                        # "anime_{}".format(j[1]) テーブルへの insert
                        c.execute('select * from anime_{0} where anime_id={1} and {0}_id={2}'.format(j[1], anime_id, content_id))
                        if len(c.fetchall()) == 0:
                            c.execute('insert into anime_{0} values ({1}, {2})'.format(j[1], anime_id, content_id))
                        print(schema + ": " + content.text)

                    c.close()
                    insertlists.remove(j)
                    self.connection.commit()

    def _check_table(self, content, table):
        c = self.connection.cursor()
        c.execute('select * from {0} where name="{1}"'.format(table, content))
        tmp = c.fetchall()
        if len(tmp) == 0:
            return True
        else:
            return False

    def _check_ordinal(self, program):
        ordinal = program.find("span", {"class": "count"}).text.replace("#", "")
        return ordinal + "話"

    def _broad_time(self, program, time_ago):  # time_age = [時,分]
        regex = "^([0-9]{2}):([0-9]{2})-([0-9]{2}):([0-9]{2}).*$"
        start_hour = int(re.sub(r"{}".format(regex), r"\1", program["title"]))
        start_minute = int(re.sub(r"{}".format(regex), r"\2", program["title"]))
        end_hour = int(re.sub(r"{}".format(regex), r"\3", program["title"]))
        end_minute = int(re.sub(r"{}".format(regex), r"\4", program["title"]))
        if start_hour >= 6:
            start_time = datetime.datetime(self.time.year, self.time.month, self.time.day, start_hour, start_minute, 0)
            if end_hour >= 6:
                end_time = datetime.datetime(self.time.year, self.time.month, self.time.day, end_hour, end_minute, 0)
            else:
                end_time = datetime.datetime(self.time.year, self.time.month, self.time.day + 1, end_hour, end_minute, 0)
        else:
            start_time = datetime.datetime(self.time.year, self.time.month, self.time.day + 1, start_hour, start_minute, 0)
            end_time = datetime.datetime(self.time.year, self.time.month, self.time.day + 1, end_hour, end_minute, 0)
        return start_time, end_time

    def _time_check(self, program, time_ago):  # time_age = [時,分]
        start_time = self._broad_time(program, time_ago)[0]
        end_time = self._broad_time(program, time_ago)[1]
        check_time = self.time + datetime.timedelta(hours=time_ago[0]) + datetime.timedelta(minutes=time_ago[1])
        if start_time <= check_time and check_time < end_time:
            return True
        else:
            return False

    def _broadcaster_check(self, program):
        for i in self.broadcaster:
            if program.find("a", {"class": "v3ch"}).text == i:
                return i
        return "_"

    def _return_soup(self, path):
        response = requests.get(self.URL + path)
        if response.status_code == 404:
            sys.stderr.write('> Error: URL page notfound.\n')
            return
        html = response.text.encode('utf-8', 'ignore')
        return BeautifulSoup(html, "lxml")

    def _toot_with_picture(self, program, broadcaster, message, mastodon):
        title = program.find("a", {"class": "v3title"}).text
        atime = program["title"]
        weekday = self._check_weekday()
        toot = title + "\n" + broadcaster + ": " + weekday + " " + atime + "\n" + "\n" + message
        print("===")
        print(toot)
        c = self.connection.cursor()
        c.execute('select anime_id from anime where name="{}"'.format(title))
        try:
            anime_id = c.fetchall()[0][0]
            print("{0}/.images/{1}.jpg".format(os.path.expanduser('~'), anime_id))
            media_files = [mastodon.media_post(media, "image/jpeg") for media in ["{0}/.images/{1}.jpg".format(os.path.expanduser('~'), anime_id)]]
            mastodon.status_post(status=toot, media_ids=media_files)
            print("> {0} toot with picture.".format(title))
        except:
            sys.stderr.write("> Error: '{}' is not in element of database (> anime table)\n".format(title))
            mastodon.toot(toot)
            print("> {0} toot.".format(title))
        finally:
            c.close()

    def _tweet_with_picture(self, program, broadcaster, message, api):
        title = program.find("a", {"class": "v3title"}).text
        atime = program["title"]
        weekday = self._check_weekday()
        tweet = title + "\n" + broadcaster + ": " + weekday + " " + atime + "\n" + "\n" + message
        print("===")
        print(tweet)
        c = self.connection.cursor()
        c.execute('select anime_id from anime where name="{}"'.format(title))
        try:
            anime_id = c.fetchall()[0][0]
            api.update_with_media(filename="{0}/.images/{1}.jpg".format(os.path.expanduser('~'), anime_id), status=tweet)
            print("> {0} tweet with picture.".format(title))
        except:
            sys.stderr.write("> Error: '{}' is not in element of database (> anime table)\n".format(title))
            api.update_status(status=tweet)
            print("> {0} tweet.".format(title))
        finally:
            c.close()

    def _check_weekday(self):
        if self.time.weekday() == 0:
            return "月曜"
        elif self.time.weekday() == 1:
            return "火曜"
        elif self.time.weekday() == 2:
            return "水曜"
        elif self.time.weekday() == 3:
            return "木曜"
        elif self.time.weekday() == 4:
            return "金曜"
        elif self.time.weekday() == 5:
            return "土曜"
        elif self.time.weekday() == 6:
            return "日曜"
        else:
            return "_"

    def _check_season(self):
        if 1 <= self.time.month and self.time.month <= 3:
            return "winter"
        elif 4 <= self.time.month and self.time.month <= 6:
            return "spring"
        elif 7 <= self.time.month and self.time.month <= 9:
            return "summer"
        elif 10 <= self.time.month and self.time.month <= 12:
            return "autumn"

    def _escaping(self, title):
        escape_list = ['\\', '/', ':', '*', '?', '"', '>', '<', '|']
        for i in escape_list:
            title = title.replace(i, " ")
        return title
