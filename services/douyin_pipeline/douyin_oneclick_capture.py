import os
import re
import sys
import html
import json
import time
import shutil
import urllib.parse
import subprocess
from pathlib import Path

import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"

def find_streams(text):
    variants = [
        text,
        html.unescape(text),
        urllib.parse.unquote(text),
        urllib.parse.unquote(html.unescape(text)),
    ]

    more = []
    for t in variants:
        more.append(
            t.replace("\\/", "/")
             .replace("\\u002F", "/")
             .replace("\\u0026", "&")
        )
    variants.extend(more)

    patterns = [
        r'https?://[^"\'<>\s\\]+?\.flv(?:\?[^"\'<>\s\\]+)?',
        r'https?://[^"\'<>\s\\]+?\.m3u8(?:\?[^"\'<>\s\\]+)?',
    ]

    found = []
    for t in variants:
        for pat in patterns:
            for u in re.findall(pat, t):
                u = html.unescape(urllib.parse.unquote(u))
                u = u.replace("\\/", "/").replace("\\u002F", "/").replace("\\u0026", "&")
                if u not in found:
                    found.append(u)

    return found

def walk_json(obj):
    found = []

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            for u in find_streams(x):
                if u not in found:
                    found.append(u)

    walk(obj)
    return found

def get_cookie_header(session):
    return "; ".join([f"{c.name}={c.value}" for c in session.cookies])


def extract_stream_urls_deep(value):
    """
    递归解析普通 JSON、JSON 字符串和转义字符串中的 FLV/M3U8 地址。
    用于兼容 live_core_sdk_data.pull_data.stream_data。
    """
    import html
    import json
    import re
    from urllib.parse import unquote

    results = []
    seen_urls = set()
    seen_objects = set()

    def add_url(url):
        if not isinstance(url, str):
            return

        url = html.unescape(url)
        url = url.replace("\\/", "/")
        url = url.replace("\\u0026", "&")
        url = url.replace("\\u003d", "=")
        url = url.strip().strip('"').strip("'")

        if url.startswith("//"):
            url = "https:" + url

        lower = url.lower()

        if not url.startswith(("http://", "https://")):
            return

        if ".flv" not in lower and ".m3u8" not in lower:
            return

        if url not in seen_urls:
            seen_urls.add(url)
            results.append(url)

    def walk(obj, depth=0):
        if depth > 20:
            return

        if isinstance(obj, (dict, list)):
            obj_id = id(obj)
            if obj_id in seen_objects:
                return
            seen_objects.add(obj_id)

        if isinstance(obj, dict):
            for key, item in obj.items():
                walk(key, depth + 1)
                walk(item, depth + 1)
            return

        if isinstance(obj, (list, tuple, set)):
            for item in obj:
                walk(item, depth + 1)
            return

        if not isinstance(obj, str):
            return

        raw = html.unescape(obj)
        raw = raw.replace("\\/", "/")
        raw = raw.replace("\\u0026", "&")
        raw = raw.replace("\\u003d", "=")

        # 提取字符串里直接存在的URL
        for candidate in re.findall(
            r'https?://[^\s"\'<>]+',
            raw,
            flags=re.IGNORECASE,
        ):
            add_url(candidate.rstrip(")},]"))

        stripped = raw.strip()

        # 尝试解析普通 JSON 字符串
        if (
            len(stripped) >= 2
            and stripped[0] in "[{"
            and stripped[-1] in "]}"
        ):
            try:
                nested = json.loads(stripped)
            except Exception:
                nested = None

            if nested is not None and nested is not obj:
                walk(nested, depth + 1)

        # 尝试解析URL编码后的JSON
        if "%7B" in stripped.upper() or "%5B" in stripped.upper():
            try:
                decoded = unquote(stripped)
                if decoded != stripped:
                    walk(decoded, depth + 1)
            except Exception:
                pass

    walk(value)
    return results


def extract_streams(page_url):
    web_rid = page_url.rstrip("/").split("/")[-1]

    session = requests.Session()
    session.headers.update({
        "User-Agent": UA,
        "Referer": "https://live.douyin.com/",
        "Origin": "https://live.douyin.com",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })

    print("[1] 访问直播页:", page_url)
    r = session.get(page_url, timeout=20, allow_redirects=True)
    print("    PAGE_STATUS:", r.status_code)
    Path("douyin_page_debug.html").write_text(r.text, encoding="utf-8")

    found = find_streams(r.text)

    # 新版页面中可能把直播流放在转义JSON字符串里
    for u in extract_stream_urls_deep(r.text):
        if u not in found:
            found.append(u)

    print("[2] 请求 web enter API")
    api_url = "https://live.douyin.com/webcast/room/web/enter/"
    params = {
        "aid": "6383",
        "app_name": "douyin_web",
        "live_id": "1",
        "device_platform": "web",
        "language": "zh-CN",
        "enter_from": "web_live",
        "cookie_enabled": "true",
        "screen_width": "1920",
        "screen_height": "1080",
        "browser_language": "zh-CN",
        "browser_platform": "Win32",
        "browser_name": "Chrome",
        "browser_version": "126.0.0.0",
        "web_rid": web_rid,
        "room_id_str": "",
        "is_need_double_stream": "false",
    }

    ar = session.get(api_url, params=params, timeout=20)
    print("    API_STATUS:", ar.status_code)
    Path("douyin_api_debug.json").write_text(ar.text, encoding="utf-8")

    try:
        data = ar.json()

        # 保留旧解析逻辑
        for u in walk_json(data):
            if u not in found:
                found.append(u)

        # 兼容新版 live_core_sdk_data.pull_data.stream_data
        # stream_data 通常是一段嵌套JSON字符串，必须继续 json.loads
        for u in extract_stream_urls_deep(data):
            if u not in found:
                found.append(u)

        # 输出最小调试信息，方便判断API是否真的返回直播数据
        api_data = data.get("data") if isinstance(data, dict) else None
        if isinstance(api_data, dict):
            rooms = api_data.get("data") or []
            print("    API_DATA_KEYS:", list(api_data.keys())[:30])
            print(
                "    API_ROOM_COUNT:",
                len(rooms) if isinstance(rooms, list) else 0,
            )
            print("    API_ROOM_STATUS:", api_data.get("room_status"))

    except Exception as exc:
        print("    API_JSON_PARSE_ERROR:", repr(exc))

        for u in find_streams(ar.text):
            if u not in found:
                found.append(u)

        for u in extract_stream_urls_deep(ar.text):
            if u not in found:
                found.append(u)

    cookie_header = get_cookie_header(session)
    Path("douyin_cookie_header.txt").write_text(cookie_header, encoding="utf-8")

    return found, cookie_header

def test_stream(stream_url, cookie_header, page_url):
    headers = (
        f"Referer: {page_url}\r\n"
        f"Origin: https://live.douyin.com\r\n"
        f"Cookie: {cookie_header}\r\n"
    )

    test_out = "test_stream_10s.mp4"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-user_agent", UA,
        "-headers", headers,
        "-i", stream_url,
        "-t", "10",
        "-c", "copy",
        test_out,
    ]

    print("[TEST] 测试流地址:")
    print(stream_url)

    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    ok = Path(test_out).exists() and Path(test_out).stat().st_size > 10000

    if ok:
        print("[OK] 10 秒测试成功:", test_out, Path(test_out).stat().st_size)
        return True
    else:
        print("[FAIL] 这个流不可用，ffmpeg 输出最后 20 行:")
        print("\n".join(p.stdout.splitlines()[-20:]))
        try:
            Path(test_out).unlink()
        except FileNotFoundError:
            pass
        return False

def record_segment(stream_url, cookie_header, page_url, name, seconds=120):
    out_root = Path("output/douyin_live_dataset") / name
    video_dir = out_root / "video"
    audio_dir = out_root / "audio"
    text_dir = out_root / "text"
    meta_dir = out_root / "metadata"
    log_dir = out_root / "logs"

    for d in [video_dir, audio_dir, text_dir, meta_dir, log_dir]:
        d.mkdir(parents=True, exist_ok=True)

    headers = (
        f"Referer: {page_url}\r\n"
        f"Origin: https://live.douyin.com\r\n"
        f"Cookie: {cookie_header}\r\n"
    )

    out_video = video_dir / f"{time.strftime('%Y%m%d_%H%M%S')}.mp4"

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-user_agent", UA,
        "-headers", headers,
        "-rw_timeout", "15000000",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-i", stream_url,
        "-t", str(seconds),
        "-map", "0:v?",
        "-map", "0:a?",
        "-c", "copy",
        str(out_video),
    ]

    print("[3] 开始录制 2 分钟:", out_video)
    with open(log_dir / "ffmpeg.log", "w", encoding="utf-8") as f:
        subprocess.run(cmd, stdout=f, stderr=f)

    if not out_video.exists() or out_video.stat().st_size <= 10000:
        print("[FAIL] 视频没有录成功，请看日志:")
        print(log_dir / "ffmpeg.log")
        return False

    print("[OK] 视频完成:", out_video, out_video.stat().st_size)

    stem = out_video.stem
    out_audio = audio_dir / f"{stem}.wav"
    out_text = text_dir / f"{stem}.txt"
    out_meta = meta_dir / f"{stem}.json"

    print("[4] 抽音频:", out_audio)
    subprocess.run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(out_video),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-acodec", "pcm_s16le",
        str(out_audio),
    ], check=False)

    out_text.write_text("[未启用语音转写；本次先验证视频和音频采集是否跑通]", encoding="utf-8")

    meta = {
        "source_name": name,
        "page_url": page_url,
        "stream_url": stream_url,
        "video_path": str(out_video),
        "audio_path": str(out_audio),
        "text_path": str(out_text),
        "segment_seconds": seconds,
        "status": "ok",
    }
    out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[OK] 全部完成")
    print("video:", out_video)
    print("audio:", out_audio)
    print("text :", out_text)
    print("meta :", out_meta)
    return True

def main():
    if len(sys.argv) < 3:
        print("用法:")
        print("python3 douyin_oneclick_capture.py account1 https://live.douyin.com/808207714751")
        sys.exit(1)

    name = sys.argv[1]
    page_url = sys.argv[2]

    if not shutil.which("ffmpeg"):
        print("没有 ffmpeg")
        sys.exit(2)

    streams, cookie_header = extract_streams(page_url)

    print("\n[FOUND_STREAMS]")
    for i, u in enumerate(streams, 1):
        print(f"[{i}] {u}")

    if not streams:
        print("[FAIL] 没找到 flv/m3u8。需要浏览器 Network 复制真实流地址。")
        sys.exit(3)

    print("\n[COOKIE]")
    print(cookie_header[:300] + ("..." if len(cookie_header) > 300 else ""))

    # 优先测试 flv，然后 m3u8
    streams = sorted(streams, key=lambda x: (".flv" not in x, ".m3u8" not in x, len(x)))

    good = None
    for u in streams:
        if test_stream(u, cookie_header, page_url):
            good = u
            break

    if not good:
        print("\n[最终失败] 找到了流，但全部 403 或不可播放。")
        print("这时需要从你本地浏览器 F12 -> Network 里复制 flv/m3u8 的完整请求地址，或者复制 Copy as cURL。")
        sys.exit(4)

    record_segment(good, cookie_header, page_url, name, seconds=120)

if __name__ == "__main__":
    main()
