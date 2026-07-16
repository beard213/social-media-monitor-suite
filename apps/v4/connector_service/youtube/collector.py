from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_ROOT = Path(
    os.getenv(
        "YOUTUBE_OUTPUT_ROOT",
        "/data4/home/minghuazhao/youtube-monitor-data/output",
    )
)

DEFAULT_ARCHIVE_FILE = Path(
    os.getenv(
        "YOUTUBE_ARCHIVE_FILE",
        "/data4/home/minghuazhao/youtube-monitor-data/archive/downloaded.txt",
    )
)

DEFAULT_LOG_ROOT = Path(
    os.getenv(
        "YOUTUBE_LOG_ROOT",
        "/data4/home/minghuazhao/youtube-monitor-data/logs",
    )
)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def normalize_info_files(output_root: Path) -> int:
    normalized = 0

    for info_path in output_root.rglob("*.info.json"):
        try:
            info = json.loads(info_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"跳过无法读取的文件：{info_path}，错误：{exc}")
            continue

        video_dir = info_path.parent
        video_id = str(info.get("id") or video_dir.name)

        metadata = {
            "platform": "youtube",
            "video_id": video_id,
            "title": info.get("title"),
            "description": info.get("description"),
            "webpage_url": info.get("webpage_url")
            or f"https://www.youtube.com/watch?v={video_id}",
            "channel": info.get("channel") or info.get("uploader"),
            "channel_id": info.get("channel_id") or info.get("uploader_id"),
            "upload_date": info.get("upload_date"),
            "timestamp": info.get("timestamp"),
            "duration": info.get("duration"),
            "view_count": info.get("view_count"),
            "like_count": info.get("like_count"),
            "comment_count": info.get("comment_count"),
            "live_status": info.get("live_status"),
            "thumbnail": info.get("thumbnail"),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "raw_info_file": info_path.name,
        }

        comments_output = []

        for comment in info.get("comments") or []:
            comments_output.append(
                {
                    "comment_id": comment.get("id"),
                    "text": comment.get("text"),
                    "author": comment.get("author"),
                    "author_id": comment.get("author_id"),
                    "author_url": comment.get("author_url"),
                    "like_count": comment.get("like_count"),
                    "timestamp": comment.get("timestamp"),
                    "parent": comment.get("parent"),
                    "is_favorited": comment.get("is_favorited"),
                }
            )

        write_json(video_dir / "metadata.json", metadata)
        write_json(video_dir / "comments.json", comments_output)

        manifest = {
            "platform": "youtube",
            "video_id": video_id,
            "metadata_file": "metadata.json",
            "comments_file": "comments.json",
            "comment_count_collected": len(comments_output),
            "files": sorted(
                file.name
                for file in video_dir.iterdir()
                if file.is_file()
            ),
        }

        write_json(video_dir / "manifest.json", manifest)
        normalized += 1

    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(
        description="YouTube channel/video collector",
    )

    parser.add_argument(
        "url",
        help="YouTube视频、频道、播放列表地址",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=int(os.getenv("YOUTUBE_MAX_VIDEOS", "3")),
    )
    parser.add_argument(
        "--max-comments",
        type=int,
        default=int(os.getenv("YOUTUBE_MAX_COMMENTS", "100")),
    )
    parser.add_argument(
        "--max-height",
        type=int,
        default=int(os.getenv("YOUTUBE_MAX_HEIGHT", "720")),
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="只采集元数据、评论、字幕和封面，不下载视频",
    )
    parser.add_argument(
        "--proxy",
        default=os.getenv(
            "YOUTUBE_PROXY",
            os.getenv("https_proxy", "http://127.0.0.1:7890"),
        ),
    )

    args = parser.parse_args()

    DEFAULT_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    DEFAULT_ARCHIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_LOG_ROOT.mkdir(parents=True, exist_ok=True)

    log_file = DEFAULT_LOG_ROOT / (
        datetime.now().strftime("youtube_%Y%m%d_%H%M%S.log")
    )

    output_template = str(
        DEFAULT_OUTPUT_ROOT
        / "%(channel_id,uploader_id|unknown_channel)s"
        / "%(id)s"
        / "%(id)s.%(ext)s"
    )

    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--ignore-errors",
        "--continue",
        "--no-overwrites",
        "--retries",
        "10",
        "--fragment-retries",
        "10",
        "--sleep-requests",
        "1",
        "--playlist-end",
        str(max(args.limit, 1)),
        "--download-archive",
        str(DEFAULT_ARCHIVE_FILE),
        "--write-info-json",
        "--clean-info-json",
        "--no-write-playlist-metafiles",
        "--write-comments",
        "--extractor-args",
        (
            f"youtube:max_comments="
            f"{max(args.max_comments, 0)},all,all,all,2;"
            "comment_sort=new"
        ),
        "--write-thumbnail",
        "--convert-thumbnails",
        "jpg",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "zh.*,en.*",
        "--sub-format",
        "srt/best",
        "--convert-subs",
        "srt",
        "--output",
        output_template,
    ]

    deno_path = shutil.which("deno")
    if deno_path:
        command.extend(
            [
                "--js-runtimes",
                f"deno:{deno_path}",
            ]
        )
        print("JavaScript Runtime：Deno", deno_path)
    else:
        print("警告：没有找到 Deno，请检查 PATH")

    if args.proxy:
        command.extend(["--proxy", args.proxy])

    if args.metadata_only:
        command.append("--skip-download")
    else:
        command.extend(
            [
                "--format",
                (
                    f"bv*[height<={args.max_height}]+ba/"
                    f"b[height<={args.max_height}]/b"
                ),
                "--merge-output-format",
                "mp4",
            ]
        )

    command.append(args.url)

    print("采集命令开始执行")
    print("输出目录：", DEFAULT_OUTPUT_ROOT)
    print("日志文件：", log_file)

    with log_file.open("w", encoding="utf-8") as log:
        log.write("COMMAND:\n")
        log.write(" ".join(command))
        log.write("\n\n")

        process = subprocess.run(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=os.environ.copy(),
            check=False,
        )

    normalized = normalize_info_files(DEFAULT_OUTPUT_ROOT)

    print("yt-dlp返回码：", process.returncode)
    print("标准化视频数量：", normalized)
    print("详细日志：", log_file)

    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
