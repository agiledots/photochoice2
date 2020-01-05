import sys
from bs4 import BeautifulSoup
import logging
import requests
import time
import uuid
import os
import shutil
import utils
import json
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
import datetime

WAITING_TIME = 3


def download_filename(url, path):
    # if folder is not exist, create folder
    dir_name = os.path.dirname(path)
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)

    response = requests.get(url, stream=True)
    # delay to avoid corrupted previews
    time.sleep(0.5)

    with open(path, 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)


def login(driver):

    username, password = ("", "")

    # 读取用户名和密码
    password_file = "./password.txt"
    if os.path.isfile(password_file) and os.path.exists(password_file):
        text = utils.read_file(password_file)
        username, password = text.split(":")
    else:
        print("password file is not exist, please create file 'password.txt' at current directory.")

    elem_username = driver.find_element_by_id("email")
    elem_username.send_keys(username)

    elem_password = driver.find_element_by_id("password")
    elem_password.send_keys(password)

    # 等待加载完成
    time.sleep(WAITING_TIME)

def get_events():
    # 获取活动列表
    event_list = driver.find_elements_by_css_selector("ul.eventList > li.event")
    print(len(event_list))

    # 活动名称
    events = []

    event_names = []
    for event in event_list:
        event_names.append(event.find_element_by_css_selector("span.eventName").text)

    # 获取活动的URL信息
    while len(event_names) != 0:
        driver.get("https://snapsnap.jp/family")
        time.sleep(WAITING_TIME)

        event_list = driver.find_elements_by_css_selector("ul.eventList > li.event")
        for event in event_list:
            event_item = event.find_element_by_css_selector("span.eventName")
            event_name = event_item.text
            event_date = event.find_element_by_css_selector("div.foot > div").text
            if event_item.text in event_names:
                del event_names[0]
                # 跳转到活动详细页面获取URL信息
                event_item.click()
                time.sleep(WAITING_TIME)
                #
                events.append({
                    "event_name": event_name,
                    "event_url": driver.current_url,
                    "event_date": event_date.split("：")[1]
                })
                break
    return events


if __name__ == "__main__":

    # create chrome driver
    chromedriver = "./chromedriver.exe"
    driver = webdriver.Chrome(chromedriver, chrome_options=Options());
    driver.get("https://snapsnap.jp/login")

    # 登陆
    login(driver)

    # 获取活动名称和页面URL信息
    # etc:
    # [
    #     {
    #         "event_name": "お遊戯会（わんぱくシアター）",
    #         "event_url": "https://snapsnap.jp/events/793099"
    #     },
    #     {
    #         "event_name": "ナーサリースクールいずみ大谷田 お餅つき",
    #         "event_url": "https://snapsnap.jp/events/793102"
    #     }
    # ]

    events = get_events()
    print(events)

    # 获取活动的分班分组信息
    for event in events:
        url = event.get("event_url")
        driver.get(url)
        time.sleep(WAITING_TIME)

        category = []
        listItem = driver.find_elements_by_css_selector("a.listItem")
        for item in listItem:
            category_title = item.find_element_by_css_selector("span").text
            category_url = item.get_attribute("href")

            category.append({
                "category_title": category_title,
                "category_url" : category_url,
            })

        event["category"] = category

    #
    # 获取照片详细页面的页数
    #
    for event in events:
        for category in event["category"]:
            category_title = category["category_title"]
            category_url = category["category_url"]

            driver.get(category_url)
            time.sleep(WAITING_TIME)

            page_size_option = driver.find_elements_by_css_selector("select.Select-body > option")

            page_size = 1
            for value in page_size_option:
                if page_size < int(value.text.strip()):
                    page_size = int(value.text.strip())

            category["page_size"] = page_size

    #
    # 保存数据
    #
    text = json.dumps(event, indent=4, sort_keys=False, ensure_ascii=False)
    json_file = "data_{}.json".format(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
    utils.write_file(json_file, text)



    #　下载各个页面的照片
    for event in events:
        # 以活动为单位的目录
        event_path = os.path.join("images", "%s_%s" % (event["event_date"], event["event_name"]))
        if not os.path.exists(event_path):
            os.mkdir(event_path)

        count = 0
        for category in event["category"]:
            category_title = category["category_title"]
            category_url = category["category_url"]
            page_size = category["page_size"]

            # 以活动分类为单位的目录
            category_path = os.path.join(event_path, category_title)
            if not os.path.exists(category_path):
                os.mkdir(category_path)

            for i in range(1, page_size + 1):

                driver.get("%s?page=%s" %(category_url, i))
                time.sleep(WAITING_TIME)

                # 获取照片的下载地址
                photo_list = driver.find_elements_by_css_selector("section.wholeImage > img")
                for photo in photo_list:
                    photo_url = photo.get_attribute("src")

                    count = count + 1
                    save_path = os.path.join(category_path, "{:0>5d}.jpg".format(count))

                    if os.path.isfile(save_path) and os.path.exists(save_path):
                        # 文件存在，不再下载
                        continue

                    print("downloading: %s" %save_path)
                    download_filename(photo_url, save_path)

