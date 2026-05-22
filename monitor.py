import requests
import time
import json
from requests.exceptions import RequestException

# ===================== 配置 =====================
API_URL = "http://konk.cc/customer/account/unread_conversation_list?token=7P8h36JcK8pRrBuSDIRymrOV7pHmZrnV&limit=50"
BARK_API_KEY = "xAeazNMHEvvUCEq3LsZyqa"
INTERVAL = 10
last_message_ids = {}
# =================================================

def send_bark(title, content):
    try:
        import urllib.parse
        title_enc = urllib.parse.quote(title)
        content_enc = urllib.parse.quote(content)
        bark_url = f"https://api.day.app/{BARK_API_KEY}/{title_enc}/{content_enc}/推送铃声?sound=chime"
        requests.get(bark_url, timeout=3)
        requests.get(bark_url, timeout=3)
        requests.get(bark_url, timeout=3)
    except:
        pass

def get_message_info(near_msg_str):
    try:
        msg_data = json.loads(near_msg_str)
        msg_id = str(msg_data.get("id", ""))
        raw_msg = msg_data.get("message", "").strip()
        if not raw_msg:
            return msg_id, "【图片/媒体消息】"
        return msg_id, raw_msg
    except:
        return "", "【解析失败】"

def is_bot(target_info):
    return target_info.get("bot", False) is True

def fetch_data():
    for attempt in range(99):
        try:
            resp = requests.get(
                API_URL,
                timeout=8,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Connection": "close",
                    "Cache-Control": "no-cache",
                    "Accept": "application/json"
                }
            )
            resp.raise_for_status()
            return resp.json(), "正常"
        except RequestException as e:
            err_msg = f"请求失败 ({attempt + 1}/3): {str(e)}"
            if attempt < 2:
                time.sleep(0.5)
                continue
            else:
                return None, err_msg
        except Exception as e:
            return None, f"未知错误: {str(e)}"

def check():
    global last_message_ids
    data, err = fetch_data()
    if data is None:
        print(f"[{time.strftime('%H:%M:%S')}] 接口不稳定，已自动重试 | 错误：{err}")
        return
    try:
        msg_list = data.get("data", {}).get("list", [])
        has_new = False
        for item in msg_list:
            conv_id = str(item.get("conversation_id", ""))
            username = item.get("username", "未知用户")
            target_info = item.get("target_info", {})
            near_msg_str = item.get("near_msg", "")
            now_unread = item.get("not_read_num", 0)
            if is_bot(target_info):
                continue
            msg_id, content = get_message_info(near_msg_str)
            if not msg_id:
                continue
            if conv_id not in last_message_ids or last_message_ids[conv_id] != msg_id:
                has_new = True
                last_message_ids[conv_id] = msg_id
                print("\n" + "=" * 55)
                print(f"📩 新消息提醒")
                print(f"👤 对方：{username}")
                print(f"🔢 未读：{now_unread}")
                print(f"💬 内容：{content}")
                print("=" * 55 + "\n")
                send_bark(username, content)
        if not has_new:
            print(f"[{time.strftime('%H:%M:%S')}] 正在刷新新消息，暂无新消息")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 数据解析异常，跳过本轮 | 错误：{str(e)}")

if __name__ == "__main__":
    print("✅ 消息监控已启动｜自动Bark推送｜24小时运行")
    while True:
        try:
            check()
        except:
            pass
        time.sleep(INTERVAL)
