import json
import time
import urllib.parse
from pathlib import Path

import requests
from requests.exceptions import RequestException

# ===================== 配置 =====================

API_URL = "http://konk.cc/customer/account/pending_reply_conversation_list"

API_TOKEN = "3zDGKmswPC6KXmskwvsRDgvjljWaqhpv"
BARK_API_KEY = "xAeazNMHEvvUCEq3LsZyqa"

LIMIT = 50
INTERVAL = 1  # 检查间隔：秒

# 第一次运行时是否推送现有的待回复消息
# False = 不推送历史消息，只从启动后开始推送新消息
NOTIFY_EXISTING_ON_FIRST_RUN = False

# 状态文件保存在脚本同目录
STATE_FILE = Path(__file__).with_name("pending_reply_monitor_state_v3.json")

# =================================================

session = requests.Session()


def load_state():
    """读取已见过的最新消息时间。"""
    default_state = {
        "version": 3,
        "initialized": False,
        "watermark_time": 0,
        "watermark_events": {},
    }

    if not STATE_FILE.exists():
        return default_state

    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))

        if not isinstance(state, dict) or state.get("version") != 3:
            return default_state

        return {
            "version": 3,
            "initialized": bool(state.get("initialized", False)),
            "watermark_time": int(state.get("watermark_time", 0)),
            "watermark_events": (
                state.get("watermark_events", {})
                if isinstance(state.get("watermark_events", {}), dict)
                else {}
            ),
        }

    except Exception:
        return default_state


def save_state(state):
    """保存状态，重启后依然不会误推送旧消息。"""
    try:
        temp_file = STATE_FILE.with_suffix(".tmp")
        temp_file.write_text(
            json.dumps(state, ensure_ascii=False),
            encoding="utf-8",
        )
        temp_file.replace(STATE_FILE)
    except Exception as error:
        print(f"状态保存失败：{error}")


def send_bark(title, content=""):
    """发送 Bark 通知。"""
    try:
        title_enc = urllib.parse.quote(str(title)[:100], safe="")

        bark_url = f"https://api.day.app/{BARK_API_KEY}/{title_enc}/"

        if content:
            content_enc = urllib.parse.quote(str(content)[:1000], safe="")
            bark_url = (
                f"https://api.day.app/{BARK_API_KEY}/"
                f"{title_enc}/{content_enc}/"
            )

        response = session.get(
            bark_url,
            params={"sound": "chime"},
            timeout=5,
        )
        response.raise_for_status()

    except Exception as error:
        print(f"Bark 推送失败：{error}")


def fetch_data():
    """请求待回复会话接口，失败时自动重试。"""
    for attempt in range(3):
        try:
            response = session.get(
                API_URL,
                params={
                    "token": API_TOKEN,
                    "limit": LIMIT,
                },
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                    "Cache-Control": "no-cache",
                },
                timeout=8,
            )

            response.raise_for_status()
            return response.json(), None

        except RequestException as error:
            if attempt < 2:
                time.sleep(0.5)
            else:
                return None, f"请求失败：{error}"

        except ValueError:
            return None, "接口没有返回有效 JSON 数据"

        except Exception as error:
            return None, f"未知错误：{error}"


def extract_message_list(payload):
    """兼容 data.list 和 data 直接为列表的接口格式。"""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    api_data = payload.get("data", payload)

    if isinstance(api_data, list):
        return [item for item in api_data if isinstance(item, dict)]

    if isinstance(api_data, dict):
        message_list = api_data.get("list", [])
        if isinstance(message_list, list):
            return [item for item in message_list if isinstance(item, dict)]

    return []


def get_message_info(near_msg):
    """从 near_msg 中读取消息 ID 与文字内容。"""
    try:
        if isinstance(near_msg, str):
            message_data = json.loads(near_msg)
        elif isinstance(near_msg, dict):
            message_data = near_msg
        else:
            return "", "【无法读取消息】"

        message_id = str(message_data.get("id", ""))
        content = str(message_data.get("message", "")).strip()

        if not content:
            content = "【图片、媒体或无文字消息】"

        return message_id, content

    except Exception:
        return "", "【消息解析失败】"


def get_message_time(item):
    """
    获取消息时间。
    标记“无需回复”后，旧消息会补入前 50 条；
    它的时间更早，因此不会被当作新消息。
    """
    for field in ("near_msg_time", "sort_time"):
        try:
            value = int(item.get(field, 0))
            if value > 0:
                return value
        except (TypeError, ValueError):
            pass

    return 0


def get_conversation_key(item):
    """生成唯一会话键。"""
    if item.get("unique_key"):
        return str(item["unique_key"])

    return (
        f"{item.get('platform', '')}_"
        f"{item.get('account_id', '')}_"
        f"{item.get('conversation_id', '')}"
    )


def check_pending_replies(state):
    """检查真正新增的待回复消息。"""
    data, error = fetch_data()

    if data is None:
        print(f"[{time.strftime('%H:%M:%S')}] 接口异常：{error}")
        return

    message_list = extract_message_list(data)
    current_records = []

    for item in message_list:
        target_info = item.get("target_info", {})

        # 跳过机器人消息
        if isinstance(target_info, dict) and target_info.get("bot") is True:
            continue

        conversation_key = get_conversation_key(item)
        message_id, content = get_message_info(item.get("near_msg", ""))
        message_time = get_message_time(item)

        if not conversation_key or not message_id or message_time <= 0:
            continue

        current_records.append({
            "conversation_key": conversation_key,
            "message_id": message_id,
            "message_time": message_time,
            "username": item.get("username", "未知用户"),
            "content": content,
        })

    old_watermark = state["watermark_time"]
    old_events = state["watermark_events"]
    initialized = state["initialized"]

    has_new_message = False

    # 首次运行建立基准；以后只通知比基准时间更新的消息
    if initialized or NOTIFY_EXISTING_ON_FIRST_RUN:
        for record in current_records:
            is_new = False

            # 消息时间比历史最大时间更大，是真正的新消息
            if record["message_time"] > old_watermark:
                is_new = True

            # 同一秒出现不同会话/不同消息，也需要通知
            elif (
                record["message_time"] == old_watermark
                and old_events.get(record["conversation_key"])
                != record["message_id"]
            ):
                is_new = True

            if is_new:
                has_new_message = True

                print("\n" + "=" * 55)
                print("📩 新的待回复消息")
                print(f"👤 对方：{record['username']}")
                print(f"💬 内容：{record['content']}")
                print("=" * 55)

                send_bark(
                    f"{record['username']}",
                    "新买家询单",
                )

    # 只提高水位线，绝不因“无需回复”后的旧会话补位而降低
    if current_records:
        newest_time = max(record["message_time"] for record in current_records)

        if newest_time > old_watermark:
            state["watermark_time"] = newest_time
            state["watermark_events"] = {
                record["conversation_key"]: record["message_id"]
                for record in current_records
                if record["message_time"] == newest_time
            }

        elif newest_time == old_watermark:
            for record in current_records:
                if record["message_time"] == old_watermark:
                    state["watermark_events"][record["conversation_key"]] = (
                        record["message_id"]
                    )

    state["initialized"] = True
    save_state(state)

    if not has_new_message:
        print(f"[{time.strftime('%H:%M:%S')}] 暂无新的待回复消息")


if __name__ == "__main__":
    monitor_state = load_state()

    print("✅ 待回复消息监控已启动｜自动 Bark 推送")

    while True:
        check_pending_replies(monitor_state)
        time.sleep(INTERVAL)
