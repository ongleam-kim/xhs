import datetime
import json
from time import sleep
import random
from pathlib import Path

from playwright.sync_api import sync_playwright

from xhs import DataFetchError, XhsClient, help


def sign(uri, data=None, a1="", web_session=""):
    for _ in range(10):
        try:
            with sync_playwright() as playwright:
                stealth_js_path = "/home/tom/PRJ/xhs/stealth.min.js"
                chromium = playwright.chromium

                # 如果一直失败可尝试设置成 False 让其打开浏览器，适当添加 sleep 可查看浏览器状态
                browser = chromium.launch(headless=True)

                browser_context = browser.new_context()
                browser_context.add_init_script(path=stealth_js_path)
                
                context_page = browser_context.new_page()
                context_page.goto("https://www.xiaohongshu.com")    
                
                
                browser_context.add_cookies([
                    {'name': 'a1', 'value': a1, 'domain': ".xiaohongshu.com", 'path': "/"}]
                )
                context_page.reload()
                # 这个地方设置完浏览器 cookie 之后，如果这儿不 sleep 一下签名获取就失败了，如果经常失败请设置长一点试试
                sleep(1)
                encrypt_params = context_page.evaluate("([url, data]) => window._webmsxyw(url, data)", [uri, data])
                return {
                    "x-s": encrypt_params["X-s"],
                    "x-t": str(encrypt_params["X-t"])
                }
        except Exception as e:
            print(f"exception: {e}")
            # 这儿有时会出现 window._webmsxyw is not a function 或未知跳转错误，因此加一个失败重试趴
            pass
    raise Exception("重试了这么多次还是无法签名成功，寄寄寄")


if __name__ == '__main__':
    
    cookie = "xsecappid=xhs-pc-web; a1=193a5e6cf36as87iqr2ken1f6we3p7gfwikiihgix30000293430; webId=616fc8b666578593f7c321280737e423; gid=yjq02dKdSdEiyjq02dKSi3xkqK0MYW3AFJTdT3CIyiKEd3q8qUWki3888Jjq4q88fqDYiKdi; x-user-id-pgy.xiaohongshu.com=5a3095d7e8ac2b441e001612; customerClientId=979703179568260; abRequestId=616fc8b666578593f7c321280737e423; webBuild=4.55.0; websectiga=cffd9dcea65962b05ab048ac76962acee933d26157113bb213105a116241fa6c; unread={%22ub%22:%226787b3c4000000001b00be73%22%2C%22ue%22:%226768853d000000000900e93b%22%2C%22uc%22:31}; web_session=040069b64b725923c2631337b2354b91171f73; sec_poison_id=e7cb39fc-f7a1-42d8-830d-3b17162c9662; acw_tc=0a4a5af217369478426547764ef82283af0740fb479544975e96fc14f1e781"

    xhs_client = XhsClient(cookie, sign=sign)
    print(datetime.datetime.now())

    with open("../export/urls.json", 'r') as f:
        url_data = json.load(f)
    # output 디렉토리 생성
    output_dir = Path("../output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    
    for item in url_data['urls'][:]:
        
            sleep_time = random.uniform(5, 15)
            sleep(sleep_time)
            
            for _ in range(10):

                # 即便上面做了重试，还是有可能会遇到签名失败的情况，重试即可
                try:
                    note = xhs_client.get_note_by_id(item['id'], xsec_token=item['xsec_token'])
                    # print(json.dumps(note, indent=4))
                    # print(help.get_imgs_url_from_note(note))
                    
                    # JSON 파일로 저장
                    output_file = output_dir / f"{item['id']}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(note, f, ensure_ascii=False, indent=4)
                    
                    print(f"크롤링 성공: {item['id']}")
                    print(f"저장 완료: {output_file}")
                    break
                except DataFetchError as e:
                    print(e)
                    print("失败重试一下下")
