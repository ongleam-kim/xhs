import datetime
import json

import requests

import xhs.help
from xhs import XhsClient


def sign(uri, data=None, a1="", web_session=""):
    # 填写自己的 flask 签名服务端口地址
    res = requests.post("http://localhost:5005/sign",
                        json={"uri": uri, "data": data, "a1": a1, "web_session": web_session})
    signs = res.json()
    return {
        "x-s": signs["x-s"],
        "x-t": signs["x-t"]
    }


if __name__ == '__main__':
    cookie = "a1=187d2defea8dz1fgwydnci40kw265ikh9fsxn66qs50000726043;gid=yYWfJfi820jSyYWfJfdidiKK0YfuyikEvfISMAM348TEJC28K23TxI888WJK84q8S4WfY2Sy;gid.sign=PSF1M3U6EBC/Jv6eGddPbmsWzLI=;webId=ba57f42593b9e55840a289fa0b755374;acw_tc=0a4ab81817369474189173159e4d1b52d69f7dbc2400fce449967504999702"
    xhs_client = XhsClient(cookie, sign=sign)


    # # get note info
    # note_info = xhs_client.get_note_by_id("63db8819000000001a01ead1")
    # print(datetime.datetime.now())
    # print(json.dumps(note_info, indent=2))
    # print(xhs.help.get_imgs_url_from_note(note_info))
