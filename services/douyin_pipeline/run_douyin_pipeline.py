import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


ROOT = Path(__file__).resolve().parent
SOURCES_FILE = ROOT / "live_sources.txt"
OUTPUT_ROOT = ROOT / "output" / "douyin_live_dataset"
RUN_LOG_DIR = ROOT / "run_logs"
WORK_ROOT = ROOT / "debug" / "pipeline_runs"


def read_sources(path: Path):
    sources = []

    if not path.exists():
        raise FileNotFoundError(f"找不到直播源文件: {path}")

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            print(f"[WARN] 跳过格式错误行: {line}")
            continue

        name, url = line.split("=", 1)
        name = name.strip()
        url = url.strip()

        if not name or not url:
            print(f"[WARN] 跳过空直播源: {line}")
            continue

        sources.append((name, url))

    if not sources:
        raise RuntimeError("live_sources.txt 里没有有效直播源")

    return sources


def merge_tree(src: Path, dst: Path):
    copied = []

    if not src.exists():
        return copied

    for p in src.rglob("*"):
        if not p.is_file():
            continue

        rel = p.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            stem = target.stem
            suffix = target.suffix
            i = 1
            while True:
                alt = target.with_name(f"{stem}_{i}{suffix}")
                if not alt.exists():
                    target = alt
                    break
                i += 1

        shutil.copy2(p, target)
        copied.append(target)

    return copied


def transcribe_one_wav(account_name: str, wav_path: Path):
    log_path = RUN_LOG_DIR / f"transcribe_{account_name}_{wav_path.stem}.log"

    cmd = [
        sys.executable,
        str(ROOT / "transcribe_funasr.py"),
        "--input",
        str(wav_path),
    ]

    print(f"[{account_name}] 开始转写: {wav_path}")

    with open(log_path, "w", encoding="utf-8") as f:
        p = subprocess.run(
            cmd,
            cwd=str(ROOT),
            stdout=f,
            stderr=subprocess.STDOUT,
            text=True,
        )

    if p.returncode == 0:
        print(f"[{account_name}] 转写完成: {wav_path}")
    else:
        print(f"[{account_name}] 转写失败，查看日志: {log_path}")

    return p.returncode


def capture_once(account_name: str, url: str, round_id: int, transcribe: bool):
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    workdir = WORK_ROOT / account_name / f"round_{round_id}_{timestamp}"
    workdir.mkdir(parents=True, exist_ok=True)

    RUN_LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    capture_log = RUN_LOG_DIR / f"capture_{account_name}_round{round_id}_{timestamp}.log"

    cmd = [
        sys.executable,
        str(ROOT / "douyin_oneclick_capture.py"),
        account_name,
        url,
    ]

    print("=" * 80)
    print(f"[{account_name}] 第 {round_id} 轮开始")
    print(f"[{account_name}] URL: {url}")
    print(f"[{account_name}] 日志: {capture_log.relative_to(ROOT)}")
    print("=" * 80)

    start_time = time.time()

    with open(capture_log, "w", encoding="utf-8") as f:
        p = subprocess.run(
            cmd,
            cwd=str(workdir),
            stdout=f,
            stderr=subprocess.STDOUT,
            text=True,
        )

    elapsed = time.time() - start_time

    print(f"[{account_name}] 第 {round_id} 轮采集结束，耗时 {elapsed:.1f}s，returncode={p.returncode}")

    src_account_dir = workdir / "output" / "douyin_live_dataset" / account_name
    dst_account_dir = OUTPUT_ROOT / account_name

    copied = merge_tree(src_account_dir, dst_account_dir)

    new_wavs = [
        p for p in copied
        if "/audio/" in str(p).replace("\\", "/") and p.suffix.lower() == ".wav"
    ]

    transcribe_codes = []

    if transcribe and new_wavs:
        for wav in new_wavs:
            code = transcribe_one_wav(account_name, wav)
            transcribe_codes.append(code)

    manifest = {
        "account": account_name,
        "url": url,
        "round_id": round_id,
        "timestamp": timestamp,
        "capture_returncode": p.returncode,
        "elapsed_seconds": elapsed,
        "capture_log": str(capture_log.relative_to(ROOT)),
        "workdir": str(workdir.relative_to(ROOT)),
        "copied_files": [str(x.relative_to(ROOT)) for x in copied],
        "new_wavs": [str(x.relative_to(ROOT)) for x in new_wavs],
        "transcribe_enabled": transcribe,
        "transcribe_returncodes": transcribe_codes,
    }

    manifest_dir = OUTPUT_ROOT / account_name / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = manifest_dir / f"round_{round_id}_{timestamp}.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[{account_name}] 第 {round_id} 轮完成")
    print(f"[{account_name}] 新文件数: {len(copied)}")
    print(f"[{account_name}] 新音频数: {len(new_wavs)}")
    print(f"[{account_name}] manifest: {manifest_path.relative_to(ROOT)}")

    return manifest


def monitor_source(account_name: str, url: str, max_rounds: int, transcribe: bool, pause_seconds: int):
    round_id = 1

    while True:
        try:
            capture_once(account_name, url, round_id, transcribe)
        except KeyboardInterrupt:
            print(f"[{account_name}] 收到 Ctrl+C，停止")
            break
        except Exception as e:
            print(f"[{account_name}] 第 {round_id} 轮异常: {repr(e)}")

        if max_rounds > 0 and round_id >= max_rounds:
            print(f"[{account_name}] 已达到 max_rounds={max_rounds}，停止")
            break

        round_id += 1

        if pause_seconds > 0:
            print(f"[{account_name}] 暂停 {pause_seconds}s 后进入下一轮")
            time.sleep(pause_seconds)


def main():
    parser = argparse.ArgumentParser(
        description="抖音直播持续采集管线：读取 live_sources.txt，持续每2分钟抓取视频、抽音频、转文字。"
    )
    parser.add_argument(
        "--sources",
        default=str(SOURCES_FILE),
        help="直播源文件，默认 live_sources.txt",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=0,
        help="每个直播源最多采集多少轮。0 表示一直采集，直到 Ctrl+C。",
    )
    parser.add_argument(
        "--no-transcribe",
        action="store_true",
        help="只采集 video/audio/metadata，不做 FunASR 转写。",
    )
    parser.add_argument(
        "--pause",
        type=int,
        default=0,
        help="每轮结束后暂停多少秒再进入下一轮，默认 0。",
    )
    parser.add_argument(
        "--clean-output",
        action="store_true",
        help="启动前自动清空 output/douyin_live_dataset，避免旧数据和新数据混在一起。",
    )
    parser.add_argument(
        "--clean-logs",
        action="store_true",
        help="启动前同时清空 run_logs 和 debug/pipeline_runs。",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=2,
        help="最多同时采集多少个直播源，默认 2。直播源很多时建议设置 2-4。",
    )

    args = parser.parse_args()

    sources = read_sources(Path(args.sources))

    if args.clean_output:
        print(f"[CLEAN] 删除旧输出目录: {OUTPUT_ROOT}")
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    if args.clean_logs:
        print(f"[CLEAN] 删除旧日志目录: {RUN_LOG_DIR}")
        shutil.rmtree(RUN_LOG_DIR, ignore_errors=True)
        print(f"[CLEAN] 删除旧调试目录: {WORK_ROOT}")
        shutil.rmtree(WORK_ROOT, ignore_errors=True)
        RUN_LOG_DIR.mkdir(parents=True, exist_ok=True)
        WORK_ROOT.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("[DOUYIN LIVE PIPELINE START]")
    print(f"项目目录: {ROOT}")
    print(f"直播源文件: {args.sources}")
    print(f"直播源数量: {len(sources)}")
    print(f"输出目录: {OUTPUT_ROOT}")
    print(f"max_rounds: {args.max_rounds}")
    print(f"transcribe: {not args.no_transcribe}")
    print("=" * 80)

    for name, url in sources:
        print(f"{name} = {url}")

    print("=" * 80)
    print("说明：")
    print("1. max_rounds=0 表示一直运行，直到 Ctrl+C。")
    print("2. 每轮会自动录制约 120 秒直播。")
    print("3. 每轮会生成 video/audio/text/metadata/logs。")
    print("4. 每个直播源会并行持续采集。")
    print("=" * 80)

    try:
        with ThreadPoolExecutor(max_workers=min(args.max_workers, len(sources))) as executor:
            futures = []

            for name, url in sources:
                futures.append(
                    executor.submit(
                        monitor_source,
                        name,
                        url,
                        args.max_rounds,
                        not args.no_transcribe,
                        args.pause,
                    )
                )

            for f in futures:
                f.result()

    except KeyboardInterrupt:
        print("\n[STOP] 用户手动停止 Ctrl+C")


if __name__ == "__main__":
    main()
