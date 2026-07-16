#!/usr/bin/env python3

import json
import os
import re
import signal
import subprocess
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import audit_worker


ROOT = Path(__file__).resolve().parent
ENGINE = Path("/data4/home/minghuazhao/douyin-biliup-engine")
ENGINE_CONFIG = ENGINE / "config.toml"
ENGINE_BIN = ENGINE / ".venv" / "bin" / "biliup"
ENGINE_PID = ENGINE / "run_logs" / "biliup.pid"
ENGINE_LOG = ENGINE / "run_logs" / "biliup.log"

PYTHON = ROOT / "venv" / "bin" / "python"
FFMPEG = "ffmpeg"

OUTPUT_ROOT = ROOT / "output" / "douyin_live_dataset"
RUN_LOGS = ROOT / "run_logs"

REGISTRY_FILE = ROOT / "database" / "biliup_rooms.json"
STATE_FILE = ROOT / "database" / "biliup_processed.json"

LOCK = threading.RLock()


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(path)


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def read_pid(path: Path) -> int | None:
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
        return pid if pid_alive(pid) else None
    except Exception:
        return None


def segment_time_string(seconds: int) -> str:
    seconds = max(30, min(int(seconds), 1800))
    hours, remain = divmod(seconds, 3600)
    minutes, secs = divmod(remain, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def prepare_account(account: str) -> Path:
    account_dir = OUTPUT_ROOT / account

    for name in [
        "video",
        "audio",
        "text",
        "metadata",
        "audit",
        "manifests",
    ]:
        (account_dir / name).mkdir(parents=True, exist_ok=True)

    return account_dir


def ensure_biliup_config(
    room_id: str,
    account: str,
    segment_seconds: int,
) -> bool:
    ENGINE.mkdir(parents=True, exist_ok=True)
    ENGINE_CONFIG.parent.mkdir(parents=True, exist_ok=True)

    old_text = (
        ENGINE_CONFIG.read_text(encoding="utf-8")
        if ENGINE_CONFIG.exists()
        else ""
    )

    # 清理已有全局配置，防止 TOML 重复键。
    cleaned_lines = []

    for line in old_text.splitlines():
        stripped = line.strip()

        if any(
            stripped.startswith(prefix)
            for prefix in [
                "downloader =",
                "segment_time =",
                "filename_prefix =",
                "filtering_threshold =",
                "uploader =",
                "event_loop_interval =",
                "checker_sleep =",
            ]
        ):
            continue

        cleaned_lines.append(line)

    global_config = [
        'downloader = "ffmpeg"',
        f'segment_time = "{segment_time_string(segment_seconds)}"',
        'filename_prefix = "{streamer}%Y-%m-%dT%H_%M_%S"',
        "filtering_threshold = 1",
        'uploader = "Noop"',
        "event_loop_interval = 10",
        "checker_sleep = 5",
        "",
    ]

    body = "\n".join(cleaned_lines).strip()

    section = f'[streamers."{account}"]'

    if section not in body:
        if body:
            body += "\n\n"

        body += (
            f'{section}\n'
            f'url = ["https://live.douyin.com/{room_id}"]\n'
            'tags = ["douyin"]\n'
        )

    new_text = "\n".join(global_config) + body.strip() + "\n"

    if new_text == old_text:
        return False

    backup = ENGINE_CONFIG.with_name(
        "config.toml.backup_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
    )

    if ENGINE_CONFIG.exists():
        backup.write_text(old_text, encoding="utf-8")

    ENGINE_CONFIG.write_text(new_text, encoding="utf-8")
    return True


def stop_biliup() -> None:
    pid = read_pid(ENGINE_PID)

    if not pid:
        return

    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        return

    for _ in range(20):
        if not pid_alive(pid):
            return
        time.sleep(0.5)

    try:
        os.kill(pid, signal.SIGKILL)
    except Exception:
        pass


def start_biliup(force_restart: bool = False) -> int:
    ENGINE_LOG.parent.mkdir(parents=True, exist_ok=True)

    existing_pid = read_pid(ENGINE_PID)

    if existing_pid and not force_restart:
        return existing_pid

    if existing_pid:
        stop_biliup()

    if not ENGINE_BIN.exists():
        raise RuntimeError(f"没有找到 biliup：{ENGINE_BIN}")

    log_handle = ENGINE_LOG.open("ab", buffering=0)

    process = subprocess.Popen(
        [
            str(ENGINE_BIN),
            "server",
            "--bind",
            "127.0.0.1",
            "--port",
            "19159",
            "--config",
            str(ENGINE_CONFIG),
        ],
        cwd=str(ENGINE),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    ENGINE_PID.write_text(str(process.pid), encoding="utf-8")
    return process.pid


def run_command(command: list[str], timeout: int) -> None:
    result = subprocess.run(
        command,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"命令失败 returncode={result.returncode}\n"
            f"{result.stdout[-4000:]}"
        )


def segment_id_from_file(source: Path, account: str) -> str:
    name = source.stem

    if name.startswith(account):
        name = name[len(account):]

    name = name.strip("_- ")

    if not name:
        name = datetime.fromtimestamp(
            source.stat().st_mtime
        ).strftime("%Y%m%d_%H%M%S")

    return re.sub(r"[^0-9A-Za-z_-]+", "_", name)


def process_segment(
    room_id: str,
    account: str,
    source: Path,
) -> None:
    account_dir = prepare_account(account)
    segment_id = segment_id_from_file(source, account)

    video_path = account_dir / "video" / f"{segment_id}.mp4"
    audio_path = account_dir / "audio" / f"{segment_id}.wav"
    text_path = account_dir / "text" / f"{segment_id}.txt"
    metadata_path = (
        account_dir / "metadata" / f"{segment_id}.json"
    )
    audit_path = (
        account_dir / "audit" / f"{segment_id}.audit.json"
    )

    if (
        video_path.exists()
        and text_path.exists()
        and audit_path.exists()
    ):
        return

    temp_video = video_path.with_name(video_path.name + ".tmp.mp4")
    temp_audio = audio_path.with_name(audio_path.name + ".tmp.wav")

    print(
        f"[PROCESS] room={room_id} file={source.name}",
        flush=True,
    )

    if not video_path.exists():
        run_command(
            [
                FFMPEG,
                "-y",
                "-fflags",
                "+genpts",
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-c",
                "copy",
                "-avoid_negative_ts",
                "make_zero",
                "-movflags",
                "+faststart",
                str(temp_video),
            ],
            timeout=600,
        )
        temp_video.replace(video_path)

    if not audio_path.exists():
        run_command(
            [
                FFMPEG,
                "-y",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(temp_audio),
            ],
            timeout=600,
        )
        temp_audio.replace(audio_path)

    generated_text = audio_path.with_suffix(".txt")
    generated_funasr = audio_path.with_suffix(".funasr.json")

    if not text_path.exists():
        last_error = None

        for attempt in range(1, 4):
            try:
                run_command(
                    [
                        str(PYTHON),
                        str(ROOT / "transcribe_funasr.py"),
                        "--input",
                        str(audio_path),
                    ],
                    timeout=1800,
                )
            except Exception as exc:
                last_error = exc

            # 某些情况下转写进程退出后文件稍晚写入。
            for _ in range(15):
                if generated_text.exists():
                    break
                time.sleep(1)

            if generated_text.exists():
                break

            print(
                f"[ASR_RETRY] "
                f"{source.name} attempt={attempt}",
                flush=True,
            )

            time.sleep(5)

        if not generated_text.exists():
            raise RuntimeError(
                "FunASR连续3次没有生成文本："
                f"{generated_text}; "
                f"last_error={last_error!r}"
            )

        generated_text.replace(text_path)

    funasr_target = (
        account_dir
        / "metadata"
        / f"{segment_id}.funasr.json"
    )

    if generated_funasr.exists():
        generated_funasr.replace(funasr_target)

    metadata = {
        "platform": "douyin",
        "room_id": room_id,
        "account": account,
        "segment_id": segment_id,
        "source_file": str(source),
        "video_path": str(video_path),
        "audio_path": str(audio_path),
        "text_path": str(text_path),
        "funasr_path": (
            str(funasr_target)
            if funasr_target.exists()
            else ""
        ),
        "processed_at": datetime.now().isoformat(),
        "pipeline": "biliup_ffmpeg_funasr_audit",
    }

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if audit_path.exists():
        audit_path.unlink()

    config = audit_worker.load_config()

    success = audit_worker.audit_one_text(
        text_path,
        config,
    )

    if not success or not audit_path.exists():
        raise RuntimeError(
            f"审核结果没有生成：{audit_path}"
        )

    print(
        f"[DONE] {account}/{segment_id}",
        flush=True,
    )


def processor_loop() -> None:
    retry_counts: dict[str, int] = {}

    while True:
        try:
            registry = load_json(REGISTRY_FILE, {})
            state = load_json(STATE_FILE, {})

            processed = set(
                state.get("processed", [])
            )

            failed = dict(
                state.get("failed", {})
            )

            changed = False

            # 最新注册的房间优先，防止旧积压任务堵塞新房间。
            rooms = list(registry.items())
            rooms.reverse()

            for room_id, info in rooms:
                account = info["account"]

                exact_pattern = re.compile(
                    rf"^{re.escape(account)}"
                    r"\d{4}-\d{2}-\d{2}"
                    r"T\d{2}_\d{2}_\d{2}\.flv$"
                )

                files = [
                    source
                    for source in ENGINE.glob(
                        f"{account}*.flv"
                    )
                    if exact_pattern.fullmatch(
                        source.name
                    )
                ]

                files.sort(
                    key=lambda source:
                        source.stat().st_mtime,
                    reverse=True,
                )

                source = None

                for candidate in files:
                    key = str(candidate.resolve())

                    if key not in processed:
                        source = candidate
                        break

                if source is None:
                    continue

                key = str(source.resolve())

                try:
                    process_segment(
                        room_id=room_id,
                        account=account,
                        source=source,
                    )

                except Exception as exc:
                    attempts = (
                        retry_counts.get(key, 0) + 1
                    )

                    retry_counts[key] = attempts

                    print(
                        f"[PROCESS_FAIL] "
                        f"room={room_id} "
                        f"attempt={attempts}/3 "
                        f"file={source}: {exc!r}",
                        flush=True,
                    )

                    if attempts >= 3:
                        failed[key] = {
                            "room_id": room_id,
                            "account": account,
                            "error": repr(exc),
                            "failed_at": (
                                datetime.now().isoformat()
                            ),
                        }

                        processed.add(key)
                        retry_counts.pop(key, None)
                        changed = True

                    continue

                processed.add(key)
                retry_counts.pop(key, None)
                failed.pop(key, None)
                changed = True

            if changed:
                save_json(
                    STATE_FILE,
                    {
                        "processed": sorted(processed),
                        "failed": failed,
                    },
                )

        except Exception as exc:
            print(
                f"[LOOP_ERROR] {exc!r}",
                flush=True,
            )

        time.sleep(5)

def register_room(payload: dict[str, Any]) -> dict[str, Any]:
    room_id = str(
        payload.get("room_id")
        or payload.get("web_rid")
        or payload.get("id")
        or ""
    ).strip()

    source_url = str(payload.get("source_url") or "").strip()

    if not room_id and source_url:
        room_id = (
            source_url.rstrip("/")
            .split("/")[-1]
            .split("?")[0]
        )

    if not room_id:
        raise ValueError("缺少 room_id")

    if not room_id.isdigit():
        raise ValueError(f"room_id格式错误：{room_id}")

    segment_seconds = int(
        payload.get("segment_seconds")
        or payload.get("seconds")
        or 120
    )

    account = f"v4_douyin_{room_id}"
    prepare_account(account)

    with LOCK:
        changed = ensure_biliup_config(
            room_id,
            account,
            segment_seconds,
        )

        registry = load_json(REGISTRY_FILE, {})

        registry[room_id] = {
            "room_id": room_id,
            "account": account,
            "source_url": (
                f"https://live.douyin.com/{room_id}"
            ),
            "segment_seconds": segment_seconds,
            "updated_at": datetime.now().isoformat(),
        }

        save_json(REGISTRY_FILE, registry)

        pid = start_biliup(force_restart=changed)

    return {
        "ok": True,
        "source": "biliup_bridge",
        "source_url": (
            f"https://live.douyin.com/{room_id}"
        ),
        "legacy_account_name": account,
        "external_pipeline_started": True,
        "biliup_pid": pid,
        "segment_seconds": segment_seconds,
    }


class Handler(BaseHTTPRequestHandler):

    def send_json(
        self,
        data: dict[str, Any],
        status: int = 200,
    ) -> None:
        raw = json.dumps(
            data,
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(raw)),
        )
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_json({
                "status": "ok",
                "service": "biliup-live-bridge",
                "biliup_pid": read_pid(ENGINE_PID),
                "rooms": load_json(REGISTRY_FILE, {}),
            })
            return

        self.send_json(
            {"detail": "Not Found"},
            status=404,
        )

    def do_POST(self) -> None:
        if self.path not in {
            "/v1/live/start",
            "/api/v1/live/start",
        }:
            self.send_json(
                {"detail": "Not Found"},
                status=404,
            )
            return

        try:
            length = int(
                self.headers.get("Content-Length", "0")
            )
            payload = json.loads(
                self.rfile.read(length).decode("utf-8")
            )
            result = register_room(payload)
            self.send_json(result)
        except Exception as exc:
            self.send_json(
                {
                    "ok": False,
                    "error": repr(exc),
                },
                status=400,
            )

    def log_message(self, fmt: str, *args: Any) -> None:
        print(
            "[HTTP]",
            fmt % args,
            flush=True,
        )


def main() -> None:
    RUN_LOGS.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)

    thread = threading.Thread(
        target=processor_loop,
        daemon=True,
    )
    thread.start()

    server = ThreadingHTTPServer(
        ("127.0.0.1", 18001),
        Handler,
    )

    print(
        "Biliup bridge listening on "
        "http://127.0.0.1:18001",
        flush=True,
    )

    server.serve_forever()


if __name__ == "__main__":
    main()
