import json
import time
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parent.parent

USER_FILE = ROOT / "database" / "monitor_users.json"
LIVE_SOURCE_FILE = ROOT / "live_sources.txt"


def load_users():
    if not USER_FILE.exists():
        USER_FILE.parent.mkdir(parents=True, exist_ok=True)
        USER_FILE.write_text("[]", encoding="utf-8")

    try:
        return json.loads(USER_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_users(users):
    USER_FILE.write_text(
        json.dumps(users, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def check_live_by_uid(user):
    """
    真实版本应该在这里通过主播 UID 查询抖音用户是否正在直播。

    当前先做可演示版本：
    如果该用户配置了 mock_room_id，就认为正在直播。
    这样可以先把前端、监控、采集流程跑通。
    """

    mock_room_id = str(user.get("mock_room_id", "")).strip()

    if mock_room_id:
        return {
            "live": True,
            "room_id": mock_room_id,
            "live_url": f"https://live.douyin.com/{mock_room_id}",
        }

    return {
        "live": False,
        "room_id": "",
        "live_url": "",
    }


def update_once():
    users = load_users()

    live_sources = []

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for user in users:
        user.setdefault("name", "")
        user.setdefault("uid", "")
        user.setdefault("enable", True)
        user.setdefault("status", "未检测")
        user.setdefault("room_id", "")
        user.setdefault("live_url", "")
        user.setdefault("last_check", "")
        user.setdefault("mock_room_id", "")
        user.setdefault("note", "")

        if not user.get("enable", True):
            user["status"] = "已停用"
            user["last_check"] = now
            continue

        result = check_live_by_uid(user)

        if result.get("live"):
            user["status"] = "直播中"
            user["room_id"] = result["room_id"]
            user["live_url"] = result["live_url"]

            safe_name = user["name"].strip() or user["uid"].strip()

            live_sources.append(
                f"{safe_name}={result['live_url']}"
            )

            print(f"[LIVE] {safe_name} -> {result['live_url']}")

        else:
            user["status"] = "未直播"
            user["room_id"] = ""
            user["live_url"] = ""

            print(f"[OFFLINE] {user.get('name', '')} uid={user.get('uid', '')}")

        user["last_check"] = now

    save_users(users)

    LIVE_SOURCE_FILE.write_text(
        "\n".join(live_sources) + ("\n" if live_sources else ""),
        encoding="utf-8",
    )

    print(f"[UPDATE] live_sources: {len(live_sources)}")


def main():
    print("=" * 80)
    print("[USER MONITOR START]")
    print(f"ROOT: {ROOT}")
    print(f"USER_FILE: {USER_FILE}")
    print(f"LIVE_SOURCE_FILE: {LIVE_SOURCE_FILE}")
    print("说明：当前版本使用 mock_room_id 模拟主播开播。")
    print("=" * 80)

    while True:
        try:
            update_once()
        except KeyboardInterrupt:
            print("[STOP] 用户手动停止")
            break
        except Exception as e:
            print(f"[ERROR] {repr(e)}")

        print("[SLEEP] 60秒后再次检测")
        time.sleep(60)


if __name__ == "__main__":
    main()
