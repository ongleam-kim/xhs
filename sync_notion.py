import requests
import json
from typing import Dict, Optional
import datetime
from time import sleep
import random
from pathlib import Path
import parse_json
from playwright.sync_api import sync_playwright
import glob
import os
from tqdm import tqdm
from xhs import DataFetchError, XhsClient, help
import re


pattern = r"https://www\.xiaohongshu\.com/(?:explore|discovery/item)/([a-zA-Z0-9]+)\?.*?xsec_token=([^&=]+)"

NOTION_DB_ID = "16d4f3ea5efb81bd97a7c599d2cff8d4"
NOTION_API_KEY = "secret_rfAdLYHfhpgHc2yEstyPeQT4i97R9UkA78NQh1g7B2C"
COOKIE = "abRequestId=c94168d3-aaca-5a38-9f0b-6d24064ec1af; a1=1948c94bbb9o2mwh8o7hruumqbfb3ps27g9tf8as630000233724; webId=8842f4bbadcc13b9bc6a1ac8b894d7a7; gid=yj4YSj4S08WWyj4YSj4DDkY0DjlJ6ExYlWxFjMK776ADi9q8DqUMJi888JqqWJ48DfSYJ8Ji; x-user-id-creator.xiaohongshu.com=673f3111000000001c019235; customerClientId=438249330604083; xsecappid=xhs-pc-web; webBuild=4.61.1; acw_tc=0a4acde517435143102432414e23866b444b17fffa9c346cb067440e8cb686; websectiga=6169c1e84f393779a5f7de7303038f3b47a78e47be716e7bec57ccce17d45f99; sec_poison_id=0fac9d58-1d67-47db-9ce3-3ff9aef7a660; web_session=040069b64b725923c2637ea3de354b1a6c00a9; unread={%22ub%22:%2267ebb49b000000001c0010d0%22%2C%22ue%22:%2267df53e5000000000900de13%22%2C%22uc%22:35}; loadts=1743514406803"
RETRY_CNT = 3
SLEEP_TIME= 10
HEADELESS = True
STEALTH_JS_PATH = "/home/tom/PRJ/xhs/stealth.min.js"


def sign(uri, data=None, a1="", web_session=""):
    for _ in range(RETRY_CNT):
        try:
            with sync_playwright() as playwright:
                chromium = playwright.chromium

                # 如果一直失败可尝试设置成 False 让其打开浏览器，适当添加 sleep 可查看浏览器状态
                browser = chromium.launch(headless=HEADELESS)

                browser_context = browser.new_context()
                browser_context.add_init_script(path=STEALTH_JS_PATH)

                context_page = browser_context.new_page()
                context_page.goto("https://www.xiaohongshu.com")

                browser_context.add_cookies([{"name": "a1", "value": a1, "domain": ".xiaohongshu.com", "path": "/"}])
                context_page.reload()
                # 这个地方设置完浏览器 cookie 之后，如果这儿不 sleep 一下签名获取就失败了，如果经常失败请设置长一点试试
                sleep(1)
                encrypt_params = context_page.evaluate("([url, data]) => window._webmsxyw(url, data)", [uri, data])
                return {"x-s": encrypt_params["X-s"], "x-t": str(encrypt_params["X-t"])}
        except Exception as e:
            print(f"exception: {e}")
            # 这儿有时会出现 window._webmsxyw is not a function 或未知跳转错误，因此加一个失败重试趴
            pass
    raise Exception("重试了这么多次还是无法签名成功，寄寄寄")


def getAllNotionDB():
    url = f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    all_results = []
    has_more = True
    start_cursor = None

    while has_more:
        payload = {}
        if start_cursor:
            payload["start_cursor"] = start_cursor

        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            return None

        data = response.json()
        all_results.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor", None)

    return all_results


def getNotionDB():
    url = f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    response = requests.post(url, headers=headers)

    if response.status_code == 200:
        return response.json()  # 노션 데이터베이스의 JSON 응답 반환
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None


def crawl_engagement(url: str) -> Optional[int]:
    """
    URL에서 인게이지먼트 데이터를 크롤링하는 함수
    나중에 구현 예정
    """
    pass


def update_notion_page(page_id: str, engagement: int):
    """
    노션 페이지의 인게이지먼트 값을 업데이트하는 함수
    """
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    data = {"properties": {"인게이지먼트": {"number": engagement}}}

    response = requests.patch(url, headers=headers, json=data)
    return response.status_code == 200


def save2json(notion_data):
    if notion_data:  # 데이터가 있을 경우에만 JSON 파일로 덤프
        with open("notion_data.json", "w", encoding="utf-8") as json_file:
            json.dump(notion_data, json_file, ensure_ascii=False, indent=4)  # JSON 파일로 저장
        print("데이터가 notion_data.json 파일에 저장되었습니다.")
    else:
        print("데이터를 가져오는 데 실패했습니다.")


def extract_ids(url: str) -> tuple:
    """
    URL에서 note_id와 xsec_token을 추출하는 함수

    Args:
        url (str): 샤오홍슈 URL

    Returns:
        tuple: (note_id, xsec_token) 또는 매칭 실패시 (None, None)
    """
    match = re.search(pattern, url)
    if match:
        note_id = match.group(1)
        xsec_token = match.group(2)
        return note_id, xsec_token
    return None, None


def updateNotionRow(page_id, properties):
    """
    특정 행(페이지)의 필드를 업데이트하는 함수.
    :param page_id: 업데이트할 페이지(행)의 ID
    :param properties: 업데이트할 필드를 딕셔너리 형태로 전달 (예: {"인게이지먼트": {"number": 1}})
    """

    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    payload = {"properties": properties}
    response = requests.patch(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()  # 업데이트된 결과 반환
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None


if __name__ == "__main__":
    xhs_client = XhsClient(COOKIE, sign=sign)
    notion_data = getAllNotionDB()
    
    # test_link = "https://www.xiaohongshu.com/explore/67863da8000000000100985c?app_platform=ios&app_version=8.68&share_from_user_hidden=true&xsec_source=app_share&type=normal&xsec_token=CBa8VRAXnWe40lDTj9LUIlrvWYTGC33zvbMt0EaEQ2gH8=&author_share=1&xhsshare=WeixinSession&shareRedId=Nz5IQjk9Ojw7TD05Tj8ySD02TDs8SEg8&apptime=1736851095&share_id=6e1d3e8d9ef64ac09e8242f99b3e3481&wechatWid=120f17e06cf5512f0930c914f3f464fb&wechatOrigin=menu"

    # test_page_id = "1994f3ea-5efb-81bb-b287-e524d21888cc"
    # with open("notion_data.json", "r", encoding="utf-8") as json_file:
    #     notion_data = json.loads(json_file.read())
    
    # extract engagement values
    for item in tqdm(notion_data, desc=f"update notion db .."):

        url = item["properties"]["콘텐츠링크"]["url"]
        page_id = item["id"]

        if not url:
            continue

        note_id, xsec_token = extract_ids(url)

        print(f"* url: {url}\n* note_id: {note_id}\nxsec_token: {xsec_token}\n\n")
        try:
            sleep_time = random.uniform(SLEEP_TIME, SLEEP_TIME*1.5)
            tqdm.write(f"* {sleep_time:.2f}초 대기")
            sleep(sleep_time)

            for retry in range(RETRY_CNT):
                try:
                    note = xhs_client.get_note_by_id(note_id, xsec_token=xsec_token)

                    updateNotionRow(
                        page_id,
                        {
                            "like": {"number": int(note["interact_info"]["liked_count"])},
                            "collect": {"number": int(note["interact_info"]["collected_count"])},
                            "share": {"number": int(note["interact_info"]["share_count"])},
                            "comment": {"number": int(note["interact_info"]["comment_count"])},
                        },
                    )

                    # # JSON 파일로 저장
                    # output_file = output_dir / f"{item['id']}.json"
                    # with open(output_file, "w", encoding="utf-8") as f:
                    #     json.dump(note, f, ensure_ascii=False, indent=4)

                    # tqdm.write(f"* 크롤링 성공: {item['id']}")
                    # tqdm.write(f"* 저장 완료: {output_file}\n")
                    break
                except DataFetchError as e:
                    tqdm.write(f"에러 발생 ({retry + 1}/{RETRY_CNT} 시도): {str(e)}")
                    if retry == 9:  # 마지막 시도에서 실패
                        tqdm.write(f"최종 실패: {item['id']}")
                    else:
                        tqdm.write("재시도 중...")
        except Exception as e:
            tqdm.write(f"예외 발생: {str(e)}")

