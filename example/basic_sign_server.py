import time

from flask import Flask, request
from gevent import monkey
from playwright.sync_api import sync_playwright

monkey.patch_all()

app = Flask(__name__)

A1 = ""


def get_context_page(instance, stealth_js_path):
    chromium = instance.chromium
    browser = chromium.launch(headless=False)
    context = browser.new_context()
    context.add_init_script(path=stealth_js_path)
    page = context.new_page()
    return context, page


stealth_js_path = "/Users/tom/PRJ/xhs/stealth.min.js"
print("playwright is starting")
playwright = sync_playwright().start()
browser_context, context_page = get_context_page(playwright, stealth_js_path)
context_page.goto("https://www.xiaohongshu.com")
print("Migrating to the home page of Xiaohongshu")
time.sleep(10)
context_page.reload()
time.sleep(1)
cookies = browser_context.cookies()

for cookie in cookies:
    if cookie["name"] == "a1":
        A1 = cookie["value"]
        print("Current browser cookie a1 value: " + cookie["value"] + ",Please set the a1 to be used to sign successfully")
print("Successfully migrated to the home page of Xiaohongshu, waiting for call")



def sign(uri, data, a1, web_session):
    encrypt_params = context_page.evaluate("([url, data]) => window._webmsxyw(url, data)", [uri, data])
    return {
        "x-s": encrypt_params["X-s"],
        "x-t": str(encrypt_params["X-t"])
    }


@app.route("/sign", methods=["POST"])
def hello_world():
    json = request.json
    uri = json["uri"]
    data = json["data"]
    a1 = json["a1"]
    web_session = json["web_session"]
    return sign(uri, data, a1, web_session)


@app.route("/a1", methods=["GET"])
def get_a1():
    return {'a1': A1}


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5005)
