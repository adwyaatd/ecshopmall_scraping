import json
import sys
import os
import traceback
import re
import uuid
from datetime import datetime

# import requests
from selenium import webdriver
from selenium.webdriver.chrome import options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
import boto3
from boto3.dynamodb.conditions import Key, Attr
import pytz


def headless_chrome():
    print("headless_chrome入った")
    is_dev = os.environ["HOME"]
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--lang=ja-JP")
    options.add_argument("--single-process")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280x1696")
    options.add_argument("--disable-application-cache")
    options.add_argument("--disable-infobars")
    # options.add_argument("--disable-setuid-sandbox")
    # options.add_argument('--disable-features=VizDisplayCompositor')
    # options.add_argument("--hide-scrollbars")
    # options.add_argument("--enable-logging")
    # options.add_argument("--log-level=0")
    # options.add_argument("--ignore-certificate-errors")
    options.add_argument("--homedir=/tmp")
    options.add_argument("start-maximized")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")

    if is_dev == '/Users/hosodaraimu':
        driver = webdriver.Chrome(
            "/usr/local/bin/chromedriver",
            options=options)
    else:
        options.binary_location = "/opt/python/driver/headless-chromium"
        driver = webdriver.Chrome(
            executable_path="/opt/python/driver/chromedriver",
            chrome_options=options
        )
    print("headless_chrome終わり")

    return driver


def is_findable_element(driver, attribute, attribute_value, target=None):
    #  print(attribute_value + "is_findable_element入った")
    driver.implicitly_wait(1)
    attribute = attribute.upper()

    if target and attribute == "XPATH":
        raise Exception("XPATH is invaild to find in target")

    result = driver.find_elements(getattr(By, attribute), attribute_value)
    # print(len(result))

    return bool(result)


def is_official_BASE_site(driver):
    if is_findable_element(driver, "name", "author") and driver.find_element_by_name("author").get_attribute("content") == "BASE":
        print("BASEのサイトに入ったので次のショップへ遷移")
        return True


def is_not_BASE_site(driver):
    if not is_findable_element(driver, "xpath", "//a[contains(@href,'base')]"):
        print("Base以外のサイトに入ったので次のショップへ遷移")
        return True


def scrape_shop_info(driver):
    current_url = driver.current_url
    pattern1 = re.compile("https?://[^/]+/.+")
    result = re.match(pattern1, current_url)

    if result:
        print(f"current_url--------------------: {current_url}")
        pattern2 = re.compile("https?://[^/]+/")
        home_url = re.match(pattern2, current_url).group()
        driver.get(home_url)
        shop_url = home_url
    else:
        shop_url = current_url

    shop_name = driver.title

    try:
        shop_description = driver.find_element_by_name(
            "description").get_attribute("content")
        contact_url = driver.find_element_by_xpath(
            "//a[contains(@href,'/inquiry/')]").get_attribute("href")
        shop_img_url = ""
        if is_findable_element(driver, "class_name", "logoImage"):
            shop_img_url = driver.find_element_by_class_name(
                "logoImage").get_attribute("src")
        elif is_findable_element(driver, "class_name", "cot-shopLogoImage"):
            shop_img_url = driver.find_element_by_class_name(
                "cot-shopLogoImage").get_attribute("src")
    except Exception as e:
        raise e

    shop_dict = {"shop_name": shop_name, "shop_description": shop_description,
                 "shop_url": shop_url, "contact_url": contact_url, "shop_img_url": shop_img_url}
    print(f"shop_dict: {shop_dict}")

    return shop_dict


def scrape_shop_list():
    try:
        print("start scraping shop_list")
        driver = headless_chrome()
        driver.implicitly_wait(3)

        shop_list = []
        scr_err_cnt = 0
        page_num = 1
        max_page_num = 1
        domain = "thebase.in"
        search_word = "アクセサリー"
        # base_url_list = ["developers.thebase.in", "design.thebase.in", "lp.thebase.in"]

        driver.get("https://www.google.co.jp/")
        search_bar = driver.find_element_by_name("q")
        search_bar.send_keys(f"site:*.{domain} {search_word}")
        search_bar.send_keys(Keys.ENTER)

        top_url = driver.current_url

        if "https://www.google.com/sorry/index" in top_url:
            print("google アクセスブロック 処理終了")
            return shop_list, scr_err_cnt

        while page_num <= max_page_num:
            elements = driver.find_elements_by_xpath(
                "//div[@class='yuRUbf']/a")

            if not elements:
                print("検索結果のurl(elements)取得できず")
                break

            urls = [i.get_attribute("href") for i in elements]
            for url in urls:
                print("ショップへ")
                try:
                    try:
                        print("get url")
                        driver.get(url)
                        print("after get url")
                    except Exception as e:
                        print(f"エラー! navigate.to url: {url} 次のショップへ遷移")
                        continue

                    if is_official_BASE_site(driver):
                        continue

                    if is_not_BASE_site(driver):
                        continue

                    shop_dict = scrape_shop_info(driver)

                    shop_list.append(shop_dict)
                except Exception as e:
                    print("スクレイピングエラー 次のショップへ")
                    print(traceback.format_exception_only(
                        type(e), e)[0].rstrip("\n"))
                    scr_err_cnt += 1
                    continue

            print("ショップループ終了")

            driver.get(top_url)
            page_num += 1
            print(f"next page_num: {page_num}")
            page_num_str = str(page_num)
            if is_findable_element(driver, "link_text", page_num_str):
                print("次のページへ遷移")
                driver.find_element_by_link_text(page_num_str).click()
            else:
                print("次ページなし スクレイピング終了")
                break
    except Exception as e:
        print("fatalエラー")
        driver.quit()
        raise
    else:
        print("全ページスクレイピング完了")
        driver.quit()
        return shop_list, scr_err_cnt


def fetch_all_shop_list(dynamodb):
    table_name = "ESM"
    ESM_table = dynamodb.Table(table_name)
    query_data = ESM_table.query(
        IndexName="GSI1",
        KeyConditionExpression=Key("SK").eq("shop") &
        Key("PK").begins_with("shop_")
    )
    shops = query_data["Items"]
    return shops


def remove_duplicate_within_list(shop_list):
    print("remove_duplicate_within_list")
    print(f"before shop_num: {len(shop_list)}")
    unique_shop_list = list(map(json.loads, set(map(json.dumps, shop_list))))
    print(f"after unique_shop_num: {len(unique_shop_list)}")
    return unique_shop_list


def remove_duplicate_with_DB(dynamodb, shop_list):
    print("remove_duplicate_with_DB")
    # DynamoDBから全ショップを取得 (todo範囲指定)
    all_shops_in_DB = fetch_all_shop_list(dynamodb)

    # ショップ名で検索し、DBに未登録のショップだけリスト化
    shop_names_in_DB = [shop["Data"] for shop in all_shops_in_DB]
    new_shops_list = [
        shop for shop in shop_list if shop["shop_name"] not in shop_names_in_DB]

    print(f"new_shop_num: {len(new_shops_list)}")

    return new_shops_list


# def fetch_last_shop_num(dynamodb):
#     table_name = "shopnumcounter"
#     table = dynamodb.Table(table_name)
#     last_shop_num = table.query(
#         KeyConditionExpression=Key("").eq("")
#     )
#     return last_shop_num


def make_shop_uuid():
    shop_uuid = f"shop_{str(uuid.uuid4())}"
    return shop_uuid


def get_current_datetime():
    tokyo = pytz.timezone("Asia/Tokyo")
    current_datetime = datetime.now(tokyo).strftime("%Y-%m-%d %H:%M:%S")
    return current_datetime


def insert_shop(dynamodb, shop):
    table_name = "ESM"
    ESM_table = dynamodb.Table(table_name)
    shop_uuid = make_shop_uuid()
    current_datetime = get_current_datetime()
    item = {
        "PK": shop_uuid,
        "SK": "shop",
        "Data": shop["shop_name"],
        "url": shop["shop_url"],
        "contact_url": shop["contact_url"],
        "decsription": shop["shop_description"],
        "img_url": shop["shop_img_url"],
        "is_disabled": False,
        "created_at": current_datetime,
        "modified_at": current_datetime
    }
    ESM_table.put_item(Item=item)
    return


def update_shop(dynamodb, shop):
    table_name = "ESM"
    ESM_table = dynamodb.Table(table_name)
    shop_uuid = make_shop_uuid()
    # condition = "attribute_not_exists(SK) AND attribute_not_exists(Data)"
    options = {
        "Key": {
            "SK": "shop",
            "Data": shop["shop_name"]
        },
        "UpdateExpression": "set PK = :shop_uuid, SK = :shop, #dt = :shop_name, contact_url = :contact_url, description = :description,img_url = :img_url, #url = :url",
        "ExpressionAttributeNames": {
            "#dt": "Data",
            "#url": "url"
        },
        "ExpressionAttributeValues": {
            ":shop_uuid": shop_uuid,
            ":shop": "shop",
            ":shop_name": shop["shop_name"],
            ":contact_url": shop["contact_url"],
            ":description": shop["shop_description"],
            ":img_url": shop["shop_img_url"],
            ":url": shop["shop_url"]
        },
        "ReturnValues": "UPDATED_NEW"
    }
    response = ESM_table.update_item(**options)
    return response


def read_shop_list_json(json_file_name):
    scr_err_cnt = 0
    shop_list = json.load(open(f"./shop_list/{json_file_name}", 'r'))
    print("shop_list")
    print(shop_list)

    return shop_list, scr_err_cnt


def main(event):
    dynamodb = boto3.resource("dynamodb")
    body = event["body"]
    should_scrape = body["should_scrape"]
    new_shop_cnt = 0
    updated_shop_cnt = 0
    scr_err_cnt = 0
    shop_list = body["shop_list"]
    print(should_scrape)
    print(type(should_scrape))

    shop_list, scr_err_cnt = (scrape_shop_list()) if should_scrape else (
        shop_list, scr_err_cnt)

    print("-------------------------")
    print(f"shop_list: {shop_list}")
    print("-------------------------")

    if shop_list:
        shop_list = remove_duplicate_within_list(shop_list)
        new_shop_list = remove_duplicate_with_DB(dynamodb, shop_list)

        # Todo
        existing_shop_list = []

        for new_shop in new_shop_list:
            insert_shop(dynamodb, new_shop)
            new_shop_cnt += 1

        for existing_shop in existing_shop_list:
            # update_shop(existing_shop)
            updated_shop_cnt += 1

        return new_shop_cnt, updated_shop_cnt, scr_err_cnt
    else:
        print("no result")
        return new_shop_cnt, updated_shop_cnt, scr_err_cnt


def lambda_handler(event, context):
    try:
        new_shop_cnt, updated_shop_cnt, scr_err_cnt = main(event)

        if new_shop_cnt == 0 and updated_shop_cnt == 0:
            print("no result")
            res = {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "no result!",
                    "new_shop_cnt": new_shop_cnt,
                    "updated_shop_cnt": updated_shop_cnt,
                    "scr_err_cnt": scr_err_cnt
                })
            }
        else:
            print("get result")
            res = {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "success!",
                    "new_shop_cnt": new_shop_cnt,
                    "updated_shop_cnt": updated_shop_cnt,
                    "scr_err_cnt": scr_err_cnt
                })
            }

        return res
    except Exception as e:
        print("----------")
        type_, value_, traceback_ = sys.exc_info()
        print(type_)
        print(value_)
        print(traceback_)
        print(traceback.format_exc())
        print("----------")
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": "failed!",
            })
        }
