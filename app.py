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

def login(driver, username, password):

    elem_username = driver.find_element_by_name("email")
    elem_username.send_keys(username)

    elem_password = driver.find_element_by_name("password")
    elem_password.send_keys(password)

    return driver.current_url


def get_real_image_url(image_link):
    url = None
    try:
        pattern = re.compile(r"w1_(.+?)/")
        key = re.findall(pattern, image_link)

        file_name = key[0]
        url = "http://image3.photochoice.net/r/tn_{0}/pc_watermark_6_h/0/".replace("{0}", file_name)
    except Exception as e:
        print("get_real_image_url Error: {}".format(e))
    return url


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



def download_images(driver, data):

    for event in data:
        # 以活动为单位的目录
        event_name = event["event_name"]
        event_path = os.path.join("images", event_name)
        if not os.path.exists(event_path):
            os.mkdir(event_path)

        for category in event["category"]:
            category_title = category["category_title"]
            category_url = category["category_url"]

            # 以活动分类为单位的目录
            category_path = os.path.join(event_path, category_title)
            if not os.path.exists(category_path):
                os.mkdir(category_path)

            # # 如果当前文件夹下有图片文件，表示之前已经下载过，取消当前活动的下载
            # existed_file_list = [filename for filename in os.listdir(category_path) if os.path.splitext(filename)[1] == '.jpg']
            # if existed_file_list:
            #     print("该里包含有图片文件，不进行下载！{}".format(category_path))
            #     continue

            # 获取活动分类页面的信息
            driver.get(category_url)

            # 跳转到页面最后，以时间动态加载所有图片
            # press the crtl + end key
            actionChains = ActionChains(driver)
            for i in range(20):
                actionChains.key_down(Keys.CONTROL + Keys.END).perform()
                time.sleep(0.5)
            # 等待加载完成
            time.sleep(1)

            # 获取页面所有图片略缩图的链接
            image_urls = driver.find_elements_by_css_selector("#p_list_loop img")
            count = 0

            for image_url in image_urls:
                # 获取图片真实地址
                real_image_url = get_real_image_url(image_url.get_attribute("src"))
                if not real_image_url:
                    continue

                # 下载照片
                count = count + 1
                save_path = os.path.join(category_path, "{:0>5d}.jpg".format(count))

                if os.path.isfile(save_path) and os.path.exists(save_path):
                    # 文件存在，不再下载
                    continue

                print("downloading file {} from {}".format(save_path, real_image_url))
                download_filename(real_image_url, save_path)


def filter_name(str):
    title, date = re.split("\n", str)
    title = re.split("\s", title)
    date = re.split("\s", date)
    return "{}_{}".format(date[0], "".join(title))


def get_event_list(driver):
    # 关闭弹窗
    elem_album_close = driver.find_element_by_id("modal_album_close")
    if elem_album_close:
        elem_album_close.click()

    # 等待一段时间
    time.sleep(3)

    # 获取页面所有活动列表
    # print("driver.current_url:{}".format(driver.current_url))
    event_url_list = []
    elem_event_list = driver.find_elements_by_css_selector("p.list>a.ng-binding")
    for elem_event in elem_event_list:
        event_title = elem_event.text
        event_url = elem_event.get_attribute('href')
        if not elem_event.text:
            continue

        # 标题整形
        event_title = filter_name(event_title)

        print((event_title, event_url))
        event_url_list.append((event_title, event_url))

    print("-------------get_event_list start----------------")
    print(json.dumps(event_url_list, indent=4, sort_keys=False, ensure_ascii=False))
    print("-------------get_event_list end----------------")

    return event_url_list


def get_event_category_list(driver, event_url_list):
    data = []

    # 获取活动页面子分类的链接
    for index, (event_title, event_url) in enumerate(event_url_list):
        # 跳转活动页面
        driver.get(event_url)

        category = []
        elem_category_list = driver.find_elements_by_css_selector("div.event_list table a")
        for elem_category in elem_category_list:
            category_title = elem_category.text
            category_url = elem_category.get_attribute('href')

            if not category_title:
                continue

            print(category_title, category_url)
            category.append({
                "category_title": category_title,
                "category_url": category_url
            })

        data.append({
            "event_name": event_title,
            "event_url": event_url,
            "category": category
        })

    print("-------------get_event_category_list start----------------")
    print(json.dumps(data, indent=4, sort_keys=False, ensure_ascii=False))
    print("-------------get_event_category_list end----------------")

    return data


if __name__ == "__main__":

    # create chrome driver
    chromedriver = "./chromedriver.exe"
    driver = webdriver.Chrome(chromedriver, chrome_options=Options());
    driver.get("https://snapsnap.jp/")

    # 读取用户名和密码
    text = utils.read_file("./password.txt")
    username, password = text.split(":")

    # 登陆
    login(driver, username, password)

    # 获取活动列表
    event_url_list = get_event_list(driver)

    # 获取所有活动的详细分类信息
    data = get_event_category_list(driver, event_url_list)

    # 保存数据
    text = json.dumps(data, indent=4, sort_keys=False, ensure_ascii=False)
    json_file = "data_{}.json".format(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
    utils.write_file(json_file, text)

    # 获取单一页面的照片信息
    download_images(driver, data)

    sys.exit()
