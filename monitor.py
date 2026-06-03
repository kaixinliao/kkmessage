import requests
import time
import urllib.parse
from datetime import datetime

# 关闭烦人的SSL警告
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ===================== 配置 =====================
BARK_API_KEY = "xAeazNMHEvvUCEq3LsZyqa"
INTERVAL = 1
WAIT_LIMIT = 30  # 每等待5次，刷新一次
# =================================================

last_total = 0
wait_count = 0

# Cookie
COOKIE_STRING = "sidebar_collapse=0; sl-session=XM8EekiKHmqgCRV1ptpQQw==; PHPSESSID=js1764rc2jvumgrtsu423fka6r; think_var=zh-cn; shop_keeplogin=9269%7C86400%7C1780410629%7Ccc0bbe7eb357abd1ee6d8433a3fecaaf; cf_clearance=jj5P4vkDQIVKPF9I3qel9MpI_2hnrd0zKprCJmuxgZY-1780325297-1.2.1.1-SOunXr98qaxROk1hg9B.fTmt.ZGj4sj440.Mhp1MiJchLHufEN319mnNsT4m3VpscvUROGfjRaBQG.4r2JC8aC3zuUVDchRzDXV4SVBUzB9TfWKBFIg.Gwouh2VQu3tJmjFn.o9KhDL08AFZwtW2u4ACMJxdvbXsZ01foWIVO7haFk4UJJHrxWkYLKbQWn2LqupfLfUsBAdDoc4_iK94faiQLBAd4e_M1LmX2NbdPb511Zo21kCD.un1T81TvZ1q49wT_bZYaG9pAvE5EiZZFYAC37zzlN7XZD4DxlC5ulLx.2pKHrxjAYBnO169HZB.WmpAnUFOy8tAPuw57.rLVfxfzLPHKPul8ei.DCsJ1SfEotiklk1njZPfNd_vfeIEuXVdGUgEcI_uLMg41S._o9jUdc3pynjycBH7PHmhwU0"


def send_bark(title, content):
    try:
        title_enc = urllib.parse.quote(title)
        content_enc = urllib.parse.quote(content)
        url = f"https://api.day.app/{BARK_API_KEY}/{title_enc}/{content_enc}"
        requests.get(url, timeout=3, verify=False)
    except:
        pass


# ===================== 每次都获取最新日期（自动跨天） =====================
def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")


# ===================== 同时执行：获取消息 + 更新客户端信息 =====================
def refresh_both():
    try:
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "zh-CN,zh;q=0.9",
            "content-length": "0",
            "origin": "https://tg.507.mx",
            "priority": "u=1, i",
            "sec-ch-ua": "\"Chromium\";v=\"148\", \"Google Chrome\";v=\"148\", \"Not/A)Brand\";v=\"99\"",
            "sec-ch-ua-arch": "\"x86\"",
            "sec-ch-ua-bitness": "\"64\"",
            "sec-ch-ua-full-version": "\"148.0.7778.179\"",
            "sec-ch-ua-full-version-list": "\"Chromium\";v=\"148.0.7778.179\", \"Google Chrome\";v=\"148.0.7778.179\", \"Not/A)Brand\";v=\"99.0.0.0\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": "\"\"",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-ch-ua-platform-version": "\"10.0.0\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
            "cookie": COOKIE_STRING
        }

        # 1. 获取消息
        url1 = "https://tg.507.mx/shop_hq/user/user/getnewmsgall?filter=%7B%7D&op=%7B%7D"
        requests.post(url1, headers=headers, data=b"", timeout=5, verify=False)

        # 2. 更新客户端信息
        url2 = "https://tg.507.mx/shop_hq/user/user/updateClientInfo?filter=%7B%7D&op=%7B%7D"
        res = requests.post(url2, headers=headers, data=b"", timeout=5, verify=False)

        current_time = time.strftime("%H:%M:%S")
        try:
            msg = res.json().get("msg", "执行成功")
        except:
            msg = "执行成功"
        print(f"[{current_time}] ✅ 消息刷新 + 客户端信息更新完成")

    except Exception as e:
        current_time = time.strftime("%H:%M:%S")
        print(f"[{current_time}] ❌ 执行失败")


# ===================== 每次请求都重新获取日期（自动跨天） =====================
def fetch_messages():
    # 每次都获取最新日期，跨天自动更新
    today = get_today_date()

    url = (
        f"https://tg.507.mx/shop_hq/user/message/index?addtabs=1&search=&sort=id&order=desc&offset=0&limit=20"
        f"&filter=%7B%22day_type%22%3A%22{today}%22%7D"
        f"&op=%7B%22day_type%22%3A%22%3D%22%7D&_={int(time.time() * 1000)}"
    )
    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "zh-CN,zh;q=0.9",
        "content-type": "application/json",
        "cookie": COOKIE_STRING,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "Referer": "https://tg.507.mx/shop_hq/user/message/index",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15, verify=False, allow_redirects=True)
        return resp.json()
    except requests.exceptions.JSONDecodeError:
        print(f"[{time.strftime('%H:%M:%S')}] 连接正常，等待新消息...")
        return None
    except Exception:
        print(f"[{time.strftime('%H:%M:%S')}] 请求正常")
        return None


def check_new_message():
    global last_total, wait_count
    data = fetch_messages()
    if not data:
        return

    total = data.get("total", 0)
    rows = data.get("rows", [])

    if last_total == 0:
        last_total = total
        print(f"[{time.strftime('%H:%M:%S')}] 已连接 → 当前消息总数: {total}")
        return

    if total > last_total:
        last_total = total
        wait_count = 0  # 收到新消息，重置计数
        if not rows:
            return

        msg = rows[0]
        msg_type = msg.get("type", "")
        direction = msg.get("direction", "")
        from_user_name = msg.get("from_user_name", "未知客户")
        content = msg.get("content", "")

        if msg_type == "menu": return
        if direction == "1": return
        if direction == "0":
            if msg_type == "chat":
                print("=" * 60)
                print(f"👤 客户: {from_user_name}")
                print(f"💬 消息: {content}")
                print("=" * 60)
                send_bark(f"客户消息: {from_user_name}", content)
            elif msg_type == "file":
                print("=" * 60)
                print(f"👤 客户: {from_user_name}")
                print(f"📎 文件：客户发送了文件")
                print("=" * 60)
                send_bark(f"客户文件: {from_user_name}", "【文件】客户发送了文件")
            elif msg_type == "image":
                print("=" * 60)
                print(f"👤 客户: {from_user_name}")
                print(f"🖼️ 图片：客户发送了图片")
                print("=" * 60)
                send_bark(f"客户图片: {from_user_name}", "【图片】客户发送了图片")
        return

    else:
        print(f"[{time.strftime('%H:%M:%S')}] 消息总数: {total}，等待新消息...")

        # 核心：干净计数，无锁
        wait_count += 1

        if wait_count == WAIT_LIMIT:
            refresh_both()
            wait_count = 0  # 执行完重置，下次继续！


if __name__ == "__main__":
    print("============================================================")
    print("✅ 507消息监控已启动（全自动运行）")
    print(f"📅 今天日期: {get_today_date()}")
    print("📌 支持：文本、文件、图片 全部提醒 | 机器人/自己发的 不提醒")
    print("============================================================")

    while True:
        try:
            check_new_message()
        except:
            pass
        time.sleep(INTERVAL)
