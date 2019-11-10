import requests
import urllib
import re
import os
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime
from LimitedOrderedDict import LimitedOrderedDict

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

labelDict = {
    "new": "新",
    "boil": "沸",
    "recommend": "荐",
    "hot": "热"
}


class SinaTopContent(object):
    '''
    利用爬虫抓去新浪微博Sina Weibo的热搜榜的内容，每隔一定的时间自动抓取一次。
    '''
    def __init__(self, config):
        '''
        初始化

        :param config: 包括五个子内容
            "banner"：该模块的名字，如"热搜榜"
            "base_url"：抓取网站的链接
            "outpath"：csv文件保存的路径
            "frequency"：自动抓取的频率，以s为单位
            "end_date"：自动抓取结束的时间
            "number": 话题数量
        '''
        self.banner = config['banner']
        self.base_url = config['base_url']
        self.outpath = config['outpath']
        self.frequency = config['frequency']
        self.number = config['number']
        self.end_date = pd.Timestamp(config['end_date'])

        self._maxLen = 1000
        self.contents = LimitedOrderedDict(self._maxLen)

    def _initial(self):
        '''
        初始化

        :return:
        '''
        if os.path.exists(self.outpath):
            os.makedirs(self.outpath)

        if self.end_date < datetime.now():
            raise TimeoutError("'end_date' is later than now!")


    def get_topcontent(self):
        '''
        爬虫的主模块

        :return:
        '''
        now = datetime.now().strftime("%Y%m%d-%H%M%S")
        print(now)
        self.contents[now] = {}


        pd.DataFrame(
            columns=['rank', 'name', 'number', 'label', 'url']
        )

        r = requests.get(self.base_url)
        html = r.text.replace(" ", "")
        html = re.sub(r'\n', '', html)

        raws = re.findall(
            ''.join(
                [
                    r'<tdclass=\"td-01ranktop\">(.*?)<\/td><tdclass=\"td-02\"><a(.*?)\&Refer=top\"',
                    r'(.*?)<\/a><span>(.*?)<\/span><\/td><tdclass=\"td-03\">(.*?)<\/td>',
                ]
            ),
            html
        )

        for raw in raws:
            try:
                raw_rank = np.int(raw[0])
                raw_name = urllib.parse.unquote(re.findall(r'=\"\/weibo\?q=(.*?)', raw[1])[0])
                if raw_rank <= self.number:
                    content = {}
                    content['rank'] = raw_rank
                    content['name'] = raw_name
                    content['number'] = np.int(raw[3])
                    raw_labels = re.findall(
                        r'<iclass=\"icon-txticon-txt-(.*?)\">', raw[4])
                    if raw_labels != []:
                        content['label'] = raw_labels[0]
                    else:
                        content['label'] = ""
                    content['url'] = 'https://s.weibo.com/weibo?q=' + raw[1] + '&Refer=top'

                    content['total'], content['news'] = self.get_eachcontent(raw[1])

                    self.contents[now][content['name']] = content
                else:
                    pass
            except Exception as e:
                print(raw_rank, "\t", raw_name, "\t", raw)
                print(e)


    def _processText(self, new):
        # for "\u200b"
        new = re.sub(r'\u200b', '', new)

        # for "<em>"
        new = re.sub(r'<em(.*?)>', '', new)
        new = re.sub(r'<\/em>', '', new)

        # for "<a>"
        new = re.sub(r'<a(.*?)>', '', new)
        new = re.sub(r'<\/a>', '', new)

        # for "<img>"
        new = re.sub(r'<img(.*?)title=\"', '', new)
        new = re.sub(r'\"alt=(.*?)>', '', new)

        # for "<i>"
        new = re.sub(r'<i(.*?)<\/i>', '', new)

        # for "<br/>"
        new = re.sub(r'<br\/>', '', new)

        return new

    def _processImage(self, new):
        if "feed_list_media_prev" in new:
            imageList = []
            imageraws = re.findall(r'<li>(.*?)<\/li>', new)
            for i in imageraws:
                try:
                    imageList.append(re.findall(r'<imgsrc=\"(.*?)\"', i)[0])
                except IndexError:
                    pass
            return imageList
        else:
            return ""

    def _processVideo(self, new):
        if "media media-video-a" in new:
            videoList = []
            videoraws = re.findall(r'<video>(.*?)<\/video>', new)
            for i in videoraws:
                try:
                    videoList.append(re.findall(r'src=\"(.*?)\"', i)[0])
                except IndexError:
                    pass
            return videoList
        else:
            return ""

    def _processFrom(self, new):
        return re.search(r'<a(.*?)>(.*?)<\/a>', new)[2]

    def get_eachcontent(self, raw_name):
        single_url = "https://s.weibo.com/hot?q=" + raw_name + "&xsort=hot&suball=1&tw=hotweibo&Refer=weibo_hot"
        r = requests.get(single_url)
        html = r.text.replace(" ", "")
        html = re.sub(r'\n', '', html)

        total = re.findall(
            r'<divclass=\"total\"><span>(.*?)<\/span><span>(.*?)<\/span><\/div>',
            html
        )
        try:
            raw_total = " ".join(list(total[0]))
        except IndexError as e:
            raw_total = ""

        single_contents = {}
        news = re.findall(
            r'<pclass=\"txt\"node-type=\"feed\_list\_content\"nick-name=\"(.*?)\">(.*?)</p>'
            + r'(.*?)<pclass=\"from\">(.*?)<\/p>',
            html
        )
        for new in news:
            content = {}
            content['name'] = new[0]
            content['text'] = self._processText(new[1])
            content['image'] = self._processImage(new[2])
            content['video'] = self._processVideo(new[3])
            content['time'] = self._processFrom(new[3])
            single_contents[new[0]] = content

        return raw_total, single_contents


    def save_output(self, outpath=None, N=1):
        '''
        保存文件的模块

        :param outpath: 文件保存路径。如若为None，则使用config.json中设置的内容
        :param N: 保存倒数N个文件
        :return:
        '''
        if outpath is None:
            outpath = self.outpath
        try:
            rever_contents = reversed(self.contents.items())

            for i in range(N):
                content = next(rever_contents)
                filename = self.banner + "_" + content[0] + ".json"
                with open(os.path.join(outpath, filename), "w") as file:
                    json.dump(content[1], file)

        except StopIteration as e:
            return ("FAIL: Only have %d contents" % i)

        else:
            return ("DONE: save %s" % filename)

    def _get_and_save(self):
        '''
        运行爬虫并保存，用于自动运行的整合函数

        :return:
        '''
        self.get_topcontent()
        res = self.save_output()
        print(res)

    def start(self):
        '''
        每隔一定的时间self.frequency自动抓取一次，结束时间为self.end_date

        :return:
        '''
        self.spider = BackgroundScheduler()

        self.spider.add_job(
            func=self._get_and_save,
            trigger=IntervalTrigger(
                end_date=self.end_date,
                seconds=self.frequency
            ),
            id="inter_job"
        )

        self.spider.start()

        while datetime.now() < self.end_date:
            time.sleep(10)

        self.spider.shutdown()

    def output(self):
        print(self.banner)
        print(self.contents)

if __name__ == "__main__":
    # root_path = os.path.dirname(os.path.abspath(__file__))
    # with open(os.path.join(root_path, "config.json"), encoding="utf8") as file:
    #     config = json.load(file)['Sina']
    #
    # sinatopcontent = SinaTopContent(config)
    # sinatopcontent.start()



    config = {
        "banner": "热搜榜",
        "base_url": "https://s.weibo.com/top/summary?cate=realtimehot",
        "outpath": "/Users/chenxg/Project/PySpider/sinaContents",
        "frequency": 10,
        "end_date": "20190108 20:00:00",
        "number": 10
    }
    sinatopcontent = SinaTopContent(config)
    sinatopcontent.get_topcontent()
    sinatopcontent.output()
    sinatopcontent.save_output(N=2)
