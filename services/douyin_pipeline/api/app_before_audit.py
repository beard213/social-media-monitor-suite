import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


BASE = Path(__file__).resolve().parent.parent

WEB_DIR = BASE / "web"
STATIC_DIR = BASE / "static"
DATABASE_DIR = BASE / "database"
RUN_LOG_DIR = BASE / "run_logs"
OUTPUT_ROOT = BASE / "output" / "douyin_live_dataset"

USER_FILE = DATABASE_DIR / "monitor_users.json"
LIVE_SOURCE_FILE = BASE / "live_sources.txt"

PID_DIR = DATABASE_DIR / "pids"
MONITOR_PID_FILE = PID_DIR / "monitor.pid"
PIPELINE_PID_FILE = PID_DIR / "pipeline.pid"

app = FastAPI(title="Douyin Live Monitor System")

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)


def ensure_files():
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    RUN_LOG_DIR.mkdir(parents=True, exist_ok=True)
    PID_DIR.mkdir(parents=True, exist_ok=True)
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    if not USER_FILE.exists():
        USER_FILE.write_text("[]", encoding="utf-8")

    if not LIVE_SOURCE_FILE.exists():
        LIVE_SOURCE_FILE.write_text("", encoding="utf-8")


def read_json(path: Path, default):
    ensure_files()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data):
    ensure_files()
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def read_users():
    users = read_json(USER_FILE, [])
    fixed = []

    for u in users:
        fixed.append(
            {
                "name": u.get("name", ""),
                "uid": u.get("uid", ""),
                "enable": bool(u.get("enable", True)),
                "status": u.get("status", "未检测"),
                "room_id": u.get("room_id", ""),
                "live_url": u.get("live_url", ""),
                "last_check": u.get("last_check", ""),
                "mock_room_id": u.get("mock_room_id", ""),
                "note": u.get("note", ""),
            }
        )

    return fixed


def write_users(users):
    write_json(USER_FILE, users)


def process_running(pid_file: Path):
    if not pid_file.exists():
        return False, None

    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except Exception:
        return False, None

    try:
        os.kill(pid, 0)
        return True, pid
    except ProcessLookupError:
        return False, pid
    except PermissionError:
        return True, pid
    except Exception:
        return False, pid


def start_process(name: str, pid_file: Path, cmd: list, log_path: Path):
    running, pid = process_running(pid_file)

    if running:
        return {
            "success": True,
            "message": f"{name} 已在运行",
            "pid": pid,
            "log": str(log_path.relative_to(BASE)) if log_path.exists() else "",
        }

    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"[WEB_START] {name}\n")
        f.write("[CMD] " + " ".join(cmd) + "\n")
        f.write("=" * 80 + "\n")
        f.flush()

    f = open(log_path, "a", encoding="utf-8")

    p = subprocess.Popen(
        cmd,
        cwd=str(BASE),
        stdout=f,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )

    pid_file.write_text(str(p.pid), encoding="utf-8")

    return {
        "success": True,
        "message": f"{name} 启动成功",
        "pid": p.pid,
        "log": str(log_path.relative_to(BASE)),
    }


def stop_process(name: str, pid_file: Path):
    running, pid = process_running(pid_file)

    if not pid:
        return {
            "success": True,
            "message": f"{name} 没有 PID 记录",
        }

    if not running:
        pid_file.unlink(missing_ok=True)
        return {
            "success": True,
            "message": f"{name} 已经不在运行",
        }

    try:
        os.killpg(pid, signal.SIGTERM)
    except Exception:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception as e:
            return {
                "success": False,
                "message": f"停止失败: {repr(e)}",
            }

    pid_file.unlink(missing_ok=True)

    return {
        "success": True,
        "message": f"{name} 已发送停止信号",
        "pid": pid,
    }


def read_live_sources():
    ensure_files()

    lines = []
    raw = LIVE_SOURCE_FILE.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines()

    for line in raw:
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" in line:
            name, url = line.split("=", 1)
            lines.append(
                {
                    "name": name.strip(),
                    "url": url.strip(),
                }
            )

    return lines


def count_files(path: Path, suffix: Optional[str] = None):
    if not path.exists():
        return 0

    if suffix:
        return len(list(path.glob(f"*{suffix}")))

    return len([x for x in path.iterdir() if x.is_file()])


def output_stats():
    stats = []

    if not OUTPUT_ROOT.exists():
        return stats

    for account_dir in sorted(OUTPUT_ROOT.iterdir()):
        if not account_dir.is_dir():
            continue

        video_dir = account_dir / "video"
        audio_dir = account_dir / "audio"
        text_dir = account_dir / "text"
        metadata_dir = account_dir / "metadata"
        audit_dir = account_dir / "audit"

        latest_text = ""

        if text_dir.exists():
            txts = sorted(
                text_dir.glob("*.txt"),
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )
            if txts:
                latest_text = txts[0].name

        stats.append(
            {
                "account": account_dir.name,
                "video_count": count_files(video_dir, ".mp4"),
                "audio_count": count_files(audio_dir, ".wav"),
                "text_count": count_files(text_dir, ".txt"),
                "metadata_count": count_files(metadata_dir, ".json"),
                "audit_count": count_files(audit_dir, ".json"),
                "latest_text": latest_text,
            }
        )

    return stats


def pipeline_supports_max_workers():
    path = BASE / "run_douyin_pipeline.py"

    if not path.exists():
        return False

    text = path.read_text(encoding="utf-8", errors="ignore")
    return "--max-workers" in text


@app.on_event("startup")
def startup():
    ensure_files()


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health():
    return {
        "success": True,
        "message": "ok",
    }


@app.get("/api/users")
def api_get_users():
    return read_users()


@app.post("/api/users/add")
def api_add_user(
    name: str = Query(...),
    uid: str = Query(...),
    mock_room_id: str = Query("", description="测试用直播间ID，可选"),
):
    users = read_users()

    uid = uid.strip()
    name = name.strip()
    mock_room_id = mock_room_id.strip()

    if not name:
        return {
            "success": False,
            "message": "主播名称不能为空",
        }

    if not uid:
        return {
            "success": False,
            "message": "主播 UID 不能为空",
        }

    for u in users:
        if u["uid"] == uid:
            return {
                "success": False,
                "message": "该 UID 已存在",
            }

    users.append(
        {
            "name": name,
            "uid": uid,
            "enable": True,
            "status": "未检测",
            "room_id": "",
            "live_url": "",
            "last_check": "",
            "mock_room_id": mock_room_id,
            "note": "",
        }
    )

    write_users(users)

    return {
        "success": True,
        "message": "添加成功",
    }


@app.delete("/api/users/{uid}")
def api_delete_user(uid: str):
    users = read_users()
    new_users = [u for u in users if u["uid"] != uid]
    write_users(new_users)

    return {
        "success": True,
        "message": "删除成功",
    }


@app.post("/api/users/{uid}/toggle")
def api_toggle_user(uid: str):
    users = read_users()

    for u in users:
        if u["uid"] == uid:
            u["enable"] = not bool(u.get("enable", True))
            write_users(users)

            return {
                "success": True,
                "message": "状态已切换",
                "enable": u["enable"],
            }

    return {
        "success": False,
        "message": "未找到该 UID",
    }


@app.get("/api/live-sources")
def api_live_sources():
    return read_live_sources()


@app.get("/api/output-stats")
def api_output_stats():
    return output_stats()


@app.get("/api/processes")
def api_processes():
    monitor_running, monitor_pid = process_running(MONITOR_PID_FILE)
    pipeline_running, pipeline_pid = process_running(PIPELINE_PID_FILE)

    return {
        "monitor": {
            "running": monitor_running,
            "pid": monitor_pid,
        },
        "pipeline": {
            "running": pipeline_running,
            "pid": pipeline_pid,
        },
    }


@app.post("/api/processes/monitor/start")
def api_start_monitor():
    cmd = [
        sys.executable,
        "-u",
        str(BASE / "monitor" / "user_monitor.py"),
    ]

    return start_process(
        "主播监控程序",
        MONITOR_PID_FILE,
        cmd,
        RUN_LOG_DIR / "user_monitor_web.log",
    )


@app.post("/api/processes/monitor/stop")
def api_stop_monitor():
    return stop_process(
        "主播监控程序",
        MONITOR_PID_FILE,
    )


@app.post("/api/processes/pipeline/start")
def api_start_pipeline(
    max_rounds: int = Query(0),
    max_workers: int = Query(2),
    clean_output: bool = Query(False),
    clean_logs: bool = Query(False),
):
    if clean_logs:
        for p in RUN_LOG_DIR.glob("*.log"):
            try:
                p.unlink()
            except Exception:
                pass

    cmd = [
        sys.executable,
        "-u",
        str(BASE / "run_douyin_pipeline.py"),
    ]

    if clean_output:
        cmd.append("--clean-output")

    if max_rounds > 0:
        cmd.extend(["--max-rounds", str(max_rounds)])

    if max_workers > 0 and pipeline_supports_max_workers():
        cmd.extend(["--max-workers", str(max_workers)])

    return start_process(
        "直播采集程序",
        PIPELINE_PID_FILE,
        cmd,
        RUN_LOG_DIR / "pipeline_web.log",
    )


@app.post("/api/processes/pipeline/stop")
def api_stop_pipeline():
    return stop_process(
        "直播采集程序",
        PIPELINE_PID_FILE,
    )


@app.get("/api/logs/{name}")
def api_read_log(name: str):
    log_parts = []

    def add_file(path: Path, title: str):
        if path.exists() and path.is_file():
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                if content.strip():
                    log_parts.append(
                        "\n"
                        + "=" * 80
                        + "\n"
                        + f"[{title}] {path.name}\n"
                        + "=" * 80
                        + "\n"
                        + content[-6000:]
                    )
            except Exception as e:
                log_parts.append(
                    f"[ERROR] 读取日志失败 {path}: {repr(e)}"
                )

    if name == "monitor":
        add_file(
            RUN_LOG_DIR / "user_monitor_web.log",
            "主播监控日志",
        )

    elif name == "pipeline":
        add_file(
            RUN_LOG_DIR / "pipeline_web.log",
            "采集总控日志",
        )

        capture_logs = sorted(
            RUN_LOG_DIR.glob("capture_*.log"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )[:10]

        transcribe_logs = sorted(
            RUN_LOG_DIR.glob("transcribe_*.log"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )[:10]

        for f in reversed(capture_logs):
            add_file(f, "直播源采集日志")

        for f in reversed(transcribe_logs):
            add_file(f, "FunASR转写日志")

    else:
        return {
            "success": False,
            "content": "未知日志类型",
        }

    if not log_parts:
        return {
            "success": False,
            "content": "暂无日志。请检查 run_logs 目录下是否存在日志文件。",
        }

    return {
        "success": True,
        "content": "\n".join(log_parts)[-10000:],
    }

@app.get("/api/monitor-status")
def api_monitor_status():
    monitor_running, monitor_pid = process_running(MONITOR_PID_FILE)
    users = read_users()
    sources = read_live_sources()

    lines = []
    lines.append("[主播监控状态]")
    lines.append("")

    if monitor_running:
        lines.append(f"运行状态: 运行中，PID={monitor_pid}")
    else:
        lines.append("运行状态: 未运行")

    lines.append("")
    lines.append("[说明]")
    lines.append("主播监控用于：基于主播 UID 自动检测是否开播，并自动写入 live_sources.txt。")
    lines.append("如果当前是直接使用 live_sources.txt 固定直播源采集，则这里没有实时监控日志是正常的。")

    lines.append("")
    lines.append("[已配置主播任务]")
    if users:
        for u in users:
            lines.append(
                f"- 名称: {u.get('name','')} | UID: {u.get('uid','')} | "
                f"启用: {u.get('enable', True)} | 状态: {u.get('status','未检测')} | "
                f"直播间: {u.get('room_id','') or '-'} | 最近检测: {u.get('last_check','') or '-'}"
            )
    else:
        lines.append("暂无主播 UID 监控任务。")

    lines.append("")
    lines.append("[当前 live_sources.txt 采集源]")
    if sources:
        for idx, s in enumerate(sources, 1):
            lines.append(f"{idx}. {s['name']} = {s['url']}")
    else:
        lines.append("当前没有采集源。")

    log_path = RUN_LOG_DIR / "user_monitor_web.log"
    if log_path.exists():
        content = log_path.read_text(encoding="utf-8", errors="ignore").strip()
        if content:
            lines.append("")
            lines.append("[最近主播监控日志]")
            lines.append(content[-5000:])
        else:
            lines.append("")
            lines.append("[最近主播监控日志]")
            lines.append("暂无运行日志。可能原因：尚未启动主播监控，或当前使用固定直播源采集。")

    return {
        "success": True,
        "content": "\n".join(lines)
    }
