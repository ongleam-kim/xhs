import datetime
import json
from time import sleep
import random
from pathlib import Path
import parse_json
from playwright.sync_api import sync_playwright
import glob
import os
from tqdm import tqdm

from xhs import DataFetchError, XhsClient, help


RETRY_CNT = 10
STEALTH_JS_PATH = "./stealth.min.js"
COOKIE = "abRequestId=c94168d3-aaca-5a38-9f0b-6d24064ec1af; a1=1948c94bbb9o2mwh8o7hruumqbfb3ps27g9tf8as630000233724; webId=8842f4bbadcc13b9bc6a1ac8b894d7a7; gid=yj4YSj4S08WWyj4YSj4DDkY0DjlJ6ExYlWxFjMK776ADi9q8DqUMJi888JqqWJ48DfSYJ8Ji; x-user-id-creator.xiaohongshu.com=673f3111000000001c019235; customerClientId=438249330604083; access-token-creator.xiaohongshu.com=customer.creator.AT-68c517462659162080523141uj8ilf5cp578vxnq; galaxy_creator_session_id=bNvRDPa1EDqlvwpeje8s0pMJf5IFNtt6zN2p; galaxy.creator.beaker.session.id=1737535736629046685042; xsecappid=xhs-pc-web; webBuild=4.56.0; acw_tc=0a0bb33017396068461498139e51081faa65f9804cc3d9f5cd8f623bcc98a3; websectiga=cf46039d1971c7b9a650d87269f31ac8fe3bf71d61ebf9d9a0a87efb414b816c; sec_poison_id=d2477159-efd9-4a75-a9bf-ce36d3a9b38f; web_session=040069b64b725923c263ec0385354bee93fc7c"
INPUT_FILE_DIR = "input"
OUTPUT_FILE_DIR = "output"
HEADELESS = True


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


def is_valid_id(id_str):
    """
    ID가 유효한지 검사하는 함수

    Args:
        id_str (str): 검사할 ID 문자열

    Returns:
        bool: 유효한 ID이면 True, 아니면 False
    """
    VALID_ID_LENGTH = 24  # "675bc154000000000103dbfa" 길이
    return isinstance(id_str, str) and len(id_str) == VALID_ID_LENGTH


def process_category(input_dir: Path, output_dir: Path):
    """
    특정 카테고리 디렉토리의 데이터를 처리하는 함수

    Args:
        input_dir (Path): 입력 디렉토리 경로
        output_dir (Path): 출력 디렉토리 경로
    """
    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    # 이미 크롤링된 파일들의 ID 목록 가져오기
    existing_ids = set()
    output_files = glob.glob(str(output_dir / "*.json"))
    for output_file in output_files:
        file_id = Path(output_file).stem
        existing_ids.add(file_id)

    print(f"* 이미 크롤링된 ID 수: {len(existing_ids)}")

    # 입력 파일들에서 고유한 ID와 xsec_token 추출
    unique_items = {}
    input_files = glob.glob(str(input_dir / "*.json"))

    # 전체 아이템 수 계산
    total_items = 0
    for input_file in input_files:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            total_items += len(data.get("data", {}).get("items", []))

    # 진행률 표시와 함께 아이템 처리
    for input_file in input_files[:]:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data.get("data", {}).get("items", []):
                post_id = item.get("id")
                xsec_token = item.get("xsec_token")

                if post_id in existing_ids:
                    continue

                if not is_valid_id(post_id):
                    continue

                if post_id and xsec_token:
                    if post_id not in unique_items:
                        unique_items[post_id] = {"id": post_id, "xsec_token": xsec_token}

    final_items = list(unique_items.values())
    print(f"* 처리할 새로운 항목 수: {len(final_items)}\n--------------\n")

    return final_items, output_dir


if __name__ == "__main__":
    input_base_dir = Path(INPUT_FILE_DIR)
    output_base_dir = Path(OUTPUT_FILE_DIR)

    # 각 카테고리 디렉토리 처리
    for category_dir in input_base_dir.iterdir():
        if not category_dir.is_dir():
            continue

        # if category_dir.name == "장군닭갈비":
        #     continue

        print(f"\n##### [ {category_dir.name} ] 시작 ######")

        # 해당 카테고리의 출력 디렉토리 경로
        category_output_dir = output_base_dir / category_dir.name

        # 카테고리별 아이템 처리
        final_items, output_dir = process_category(category_dir, category_output_dir)

        if not final_items:
            print(f"* {category_dir.name}: 처리할 새로운 항목이 없습니다.")
            continue

        # 크롤링 수행
        xhs_client = XhsClient(COOKIE, sign=sign)
        print(datetime.datetime.now())

        # 전체 크롤링 진행률 표시
        for item in tqdm(final_items[:], desc=f"{category_dir.name} 진행 중.."):
            try:
                sleep_time = random.uniform(5, 15)
                tqdm.write(f"* {sleep_time:.2f}초 대기")
                sleep(sleep_time)

                for retry in range(RETRY_CNT):
                    try:
                        note = xhs_client.get_note_by_id(item["id"], xsec_token=item["xsec_token"])
                        # JSON 파일로 저장
                        output_file = output_dir / f"{item['id']}.json"
                        with open(output_file, "w", encoding="utf-8") as f:
                            json.dump(note, f, ensure_ascii=False, indent=4)

                        tqdm.write(f"* 크롤링 성공: {item['id']}")
                        tqdm.write(f"* 저장 완료: {output_file}\n")
                        break
                    except DataFetchError as e:
                        tqdm.write(f"에러 발생 ({retry + 1}/{RETRY_CNT} 시도): {str(e)}")
                        if retry == 9:  # 마지막 시도에서 실패
                            tqdm.write(f"최종 실패: {item['id']}")
                        else:
                            tqdm.write("재시도 중...")
            except Exception as e:
                tqdm.write(f"예외 발생: {str(e)}")
                continue
