import sys
import os
import re
import datetime
from bs4 import BeautifulSoup
import requests
import tweepy
import collect_img


class AniTimeTable:

    URL = "http://cal.syoboi.jp"

    def __init__(self, time, broadcaster_list, CONSUMER_KEY="_", CONSUMER_SECRET="_", ACCESS_TOKEN="_", ACCESS_TOKEN_SECRET="_", DB_CONNECTION="_"):
        if not isinstance(time, datetime.datetime):
            sys.stderr.write('Error: class initialized error: argment type is not datetime.datetime\n')
            return
        self.time = time
        self.broadcaster = broadcaster_list
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        self.api = tweepy.API(auth)
        self.connection = DB_CONNECTION

    def show_all(self):
        soup = self._return_soup("/?date=" + self.time.strftime("%Y/%m/%d"))
        programs = soup.find("td", {"class": "v3dayCell v3cellR "}).find_all("div", {"class": "pid-item v3div"})
        for program in programs:
            sys.stdout.write(program["title"] + "\n")

    def insert_db(self):
        if self.connection == "_":
            sys.stderr.write('Error: database not initialized')
        titlelist_id = {
            "1",  # 放送中アニメ
            # "2", # ラジオ
            # "3", # ドラマ
            # "4", # 特撮
            # "5", # アニメ関連
            # "7", # OVA
            # "8", # 映画
            # "10", # 放送終了アニメ
        }
        for i in titlelist_id:
            soup = self._return_soup("/list?cat={0}".format(i))
            title_list = soup.find("table", {"class": "TitleList TableColor"})
            title_url = title_list.find_all("a")
            for j in title_url:
                title = j.text
                self._search_and_download_image(title)
                print("== " + title + " ==")
                soup = self._return_soup(j["href"])
                try:
                    staff_list = soup.find_all("table", {"class": "section staff"})
                    c = self.connection.cursor()
                    if self._check_table(title, "anime"):
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

    def now_program(self, tweet="_"):
        soup = self._return_soup("/?date=" + self.time.strftime("%Y/%m/%d"))
        programs = soup.find("td", {"class": "v3dayCell v3cellR "}).find_all("div", {"class": "pid-item v3div"})
        for program in programs:
            if self._time_check(program, 0, 0):
                broadcaster_check = self._broadcaster_check(program)
                if broadcaster_check != "_":
                    message = "放送中です。"
                    ordinal = self._check_ordinal(program)
                    if tweet.lower() == "tweet":
                        self._tweet_with_picture(program, broadcaster_check, message)
                    else:
                        title = program.find("a", {"class": "v3title"}).text
                        atime = program["title"]
                        weekday = self._check_weekday()
                        sys.stdout.write(title + "\n" + broadcaster_check + ": " + weekday + " " + atime + "\n" + ordinal + message + "\n")
                        print("===")

    def _search_and_download_image(self, title):
        response = requests.get("https://search.yahoo.co.jp/image/search?p={0}&ei=UTF-8&rkf=1".format(title))
        if response.status_code == 404:
            sys.stderr.write('Error: URL page notfound.\n')
            sys.exit(1)
        html = response.text.encode("utf-8", "ignore")
        soup = BeautifulSoup(html, "lxml")
        content = soup.find("div", {"id": "contents"})
        image_url = content.find("img")["src"]
        image = requests.get(image_url)
        with open("{0}/.images/{1}.jpg".format(os.path.expanduser('~'), title), 'wb') as myfile:
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

    def _time_check(self, program, *time_ago):  # *time_age = [時,分]
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
                end_time = datetime.datetime(self.time.year, self.time.month, self.time.day - 1, end_hour, end_minute, 0)
        else:
            start_time = datetime.datetime(self.time.year, self.time.month, self.time.day - 1, start_hour, start_minute, 0)
            end_time = datetime.datetime(self.time.year, self.time.month, self.time.day - 1, end_hour, end_minute, 0)
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
            sys.stderr.write('Error: URL page notfound.\n')
            return
        html = response.text.encode('utf-8', 'ignore')
        return BeautifulSoup(html, "lxml")

    def _tweet_with_picture(self, program, broadcaster, message):
        title = program.find("a", {"class": "v3title"}).text
        atime = program["title"]
        weekday = self._check_weekday()
        tweet = title + "\n" + broadcaster + ": " + weekday + " " + atime + "\n" + "\n" + message
        anime_id_list = self._select_database('anime_id', 'anime', 'where name = "{0}"'.format(title))
        for i in anime_id_list:
            anime_id = i[0]
            self.api.update_with_media(filename="{0}/.images/{1}.jpg".format(os.path.expanduser('~'), anime_id), status=tweet)
            sys.stdout.write("{0} tweet.\n".format(title))

    def _select_database(self, column, table, condition=""):
        try:
            c = self.connection.cursor()
            c.execute('select {0} from {1} {2}'.format(column, table, condition))
            values = c.fetchall()
            c.close()
            return values
        except:
            sys.stderr.write("Error: Database cant connected\n")
            return

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
