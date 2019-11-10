# PySpider

This is the project of *Spider of Sina and Zhihu* based Python.(Maybe more channels latter!)

* 注：该Project依赖于Python3.6

## 文件目录：

* config.json: 设置文件，每个子内容包括五项

  ```python
  {
      "banner": "该模块的名字，如'热搜榜'",
      "base_url": "抓取网站的链接",
      "outpath": "csv文件保存的路径",
      "frequency": "自动抓取的频率，以s为单位",
      "end_date": "自动抓取结束的时间",
      "number": "话题数量"
  }
  ```

* SinaSpider.py：利用爬虫抓去新浪微博Sina Weibo的热搜榜的内容，每隔一定的时间自动抓取一次。
* requirements.txt：运行所需要的依赖包

## 运行方法

首先，安装所需要的依赖包：

```
pip install -r requirements.txt
```

其次，修改*config.json*文件中所需要的设置，特别是*"outpath", "frequency", "end_date"。

最终，运行对应的.py文件

```
python SinaSpider.py
```



