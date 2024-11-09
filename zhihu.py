from time import sleep

import requests
import typing
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts
from pyecharts import options as opts
from pyecharts.charts import Scatter, Bar, Map, Pie

import secret

import platform

import os


class Model():
    """
    基类, 用来显示类的信息
    """

    def __repr__(self):
        name = self.__class__.__name__
        properties = ('{}=({})'.format(k, v) for k, v in self.__dict__.items())
        s = '\n<{} \n  {}>'.format(name, '\n  '.join(properties))
        return s


class Info(Model):
    """
    关注用户的动态信息
    """
    def __init__(self):
        self.user = ''
        self.action = ''
        self.question = ''
        self.vote = ''


def get(url, filename):
    """
    缓存, 避免重复下载网页浪费时间
    """
    folder = 'cached'
    # 建立 cached 文件夹
    if not os.path.exists(folder):
        os.makedirs(folder)

    path = os.path.join(folder, filename)
    if os.path.exists(path):
        with open(path, 'rb') as f:
            s = f.read()
            return s
    else:
        # 发送网络请求, 把结果写入到文件夹中
        r = requests.get(url)
        with open(path, 'wb') as f:
            f.write(r.content)
            return r.content


def cached_page(url):
    filename = '{}.html'.format(url.split('=', 1)[-1])
    page = get(url, filename)
    return page


def add_chrome_webdriver():
    print(platform.system())
    working_path = os.getcwd()
    library = 'library'
    path = os.path.join(working_path, library)
    os.environ['PATH'] += '{}{}{}'.format(os.pathsep, path, os.pathsep)
    print(os.environ['PATH'])


def add_cookie(browser):
    browser.delete_all_cookies()
    print('before', browser.get_cookies())
    for part in secret.cookie.split('; '):
        kv = part.split('=', 1)
        d = dict(
            name=kv[0],
            value=kv[1],
            path='/',
            domain='.zhihu.com',
            secure=True
        )
        print('cookie', d)
        browser.add_cookie(d)
    print('after', browser.get_cookies())


def scroll_to_end(browser):
    browser.execute_script('window.scrollTo(0, document.body.scrollHeight);')


def feed_from_div(div):
    """
    从一个 div 里面获取到一个电影信息
    """
    # e = pq(div)
    e = div

    # 小作用域变量用单字符
    m = Info()
    m.user = e.find_elements_by_css_selector('.UserLink-link')[0].text
    firstline = e.find_elements_by_css_selector('.FeedSource-firstline')[0].text
    m.action = firstline.split()[1]
    # print(firstline)
    m.time = firstline.split('·')[1]
    m.question = e.find_elements_by_css_selector('.ContentItem-title')[0].text
    actions = e.find_elements_by_css_selector('.ContentItem-actions')[0].text
    m.vote = actions.split()[1]
    return m


def start_crawler(browser):
    # 垃圾 chrome 有 bug https://bugs.chromium.org/p/chromium/issues/detail?id=617931
    # 不能 --user-data-dir 和 --headless 一起用
    # 改回用 cookie

    url = "https://www.zhihu.com/follow"
    # 先访问一个 url，才能设置这个 url 对应的 cookie
    browser.get('https://www.zhihu.com/404')
    add_cookie(browser)
    # sleep(1)
    # 设置好 cookie 后，刷新页面即可进入登录状态
    browser.get(url)
    # sleep(1)
    #
    while True:
        print('loop')
        cards = browser.find_elements_by_css_selector('.Card.TopstoryItem')
        for card in cards:
            try:
                source = card.find_element_by_css_selector('.FeedSource-firstline')
            except NoSuchElementException:
                pass
            else:
                if '1 天前' in source.text:
                    print('拿到了最近1天动态')
                    items = browser.find_elements_by_css_selector('.Feed')
                    feeds = [feed_from_div(i) for i in items]
                    print(feeds)
                    return feeds
                    # titles = browser.find_elements_by_css_selector('.ContentItem-title')
                    # for title in titles:
                    #     print(title.text)
                    # return
        # 当这次鼠标滚动找不到数据的时候，执行下一次滚动
        scroll_to_end(browser)


def table_base(feeds: typing.List) -> Table:
    table = Table()
    headers = ['user', 'action', 'time', 'question', 'vote']
    rows = []
    for f in feeds:
        info = [f.user, f.action, f.time, f.question, f.vote]
        rows.append(info)
        table.add(headers, rows).set_global_opts(
            title_opts=ComponentTitleOpts(title='爬取一天的关注动态', subtitle='利用无头浏览器爬取异步加载页面')
        )
    table.render('zhihu.html')
    return table


def bar_base(feeds) -> Bar:
    users = []
    user_class = []
    values = []
    for feed in feeds:
        users.append(feed.user)
        if feed.user not in user_class:
            user_class.append(feed.user)

    print(users)
    dict = {}
    for key in users:
        dict[key] = dict.get(key, 0) + 1

    print('user  class', user_class)
    print('dict', dict)
    for i in dict:
        values.append(dict[i])
    print(values)

    c = (
        Bar()
        .add_xaxis(user_class)

        .add_yaxis('', values)
        .set_global_opts(title_opts=opts.TitleOpts(title="Follower Action Count"))

    )
    c.render('zhihu_bars.html')
    return c


def pie_radius(feeds) -> Pie:
    question_class = []
    questions = []
    top10_question = []
    top10_num = []
    for feed in feeds:
        questions.append(feed.question)
        if feed.question not in question_class:
            question_class.append(feed.question)

    dict = {}
    for key in questions:
        dict[key] = dict.get(key, 0) + 1

    dict_sorted = sorted(dict.items(), key=lambda item:item[1], reverse=True)
    print(dict_sorted)

    for i in range(10):
        top10_question.append(dict_sorted[i][0])
        top10_num.append(dict_sorted[i][1])

    c = (
        Pie()
        .add(
            "",
            [list(z) for z in zip(top10_question, top10_num)],
            radius=["40%", "75%"],
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Top 10 Country"),
            legend_opts=opts.LegendOpts(
                orient="vertical", pos_top="15%", pos_left="2%"
            ),
        )
        .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c}"))
    )

    c.render('zhihu_radius.html')
    return c


def main():
    # cookie 要去掉 _xsrf _zap tgw_l7_route 这三个
    add_chrome_webdriver()

    o = Options()
    # o.add_argument("--headless")
    browser = webdriver.Chrome(chrome_options=o)
    try:
        feeds = start_crawler(browser)
        table_base(feeds)
        bar_base(feeds)
        pie_radius(feeds)
    finally:
        browser.quit()


if __name__ == '__main__':
    main()
