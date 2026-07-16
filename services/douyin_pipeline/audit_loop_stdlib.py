import argparse
import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).resolve().parent
OUTPUT_ROOT = BASE / "output" / "douyin_live_dataset"
CONFIG_FILE = BASE / "audit_config.json"


def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {
        "enabled": True,
        "base_url": "http://localhost:8080",
        "text_max_chars": 10000,
        "timeout": 300
    }


def safe_json_loads(raw):
    try:
        return json.loads(raw)
    except Exception:
        return None


def post_json(url, payload, timeout=120):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            return {
                "ok": True,
                "http_status": resp.status,
                "response_text": raw,
                "response_json": safe_json_loads(raw)
            }
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        return {
            "ok": False,
            "http_status": e.code,
            "response_text": raw,
            "response_json": safe_json_loads(raw),
            "error": repr(e)
        }
    except Exception as e:
        return {
            "ok": False,
            "http_status": None,
            "response_text": "",
            "response_json": None,
            "error": repr(e)
        }


def multipart_upload(url, file_path: Path, timeout=300, fields=None):
    fields = fields or {}
    boundary = "----DouyinAuditBoundary7MA4YWxkTrZu0gW"

    parts = []

    for name, value in fields.items():
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )

    file_bytes = file_path.read_bytes()
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8")
    )
    parts.append(file_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    body = b"".join(parts)

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body))
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            return {
                "ok": True,
                "http_status": resp.status,
                "response_text": raw,
                "response_json": safe_json_loads(raw)
            }
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        return {
            "ok": False,
            "http_status": e.code,
            "response_text": raw,
            "response_json": safe_json_loads(raw),
            "error": repr(e)
        }
    except Exception as e:
        return {
            "ok": False,
            "http_status": None,
            "response_text": "",
            "response_json": None,
            "error": repr(e)
        }


def iter_values(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from iter_values(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_values(item)


def normalize_status(value):
    if value is None:
        return None

    s = str(value).strip()

    if not s:
        return None

    lower = s.lower()

    if s in ["合规", "疑似", "违规", "未知"]:
        return s

    if lower in ["pass", "normal", "safe", "approve", "approved", "allow", "allowed"]:
        return "合规"

    if lower in ["review", "suspect", "suspicious", "warning", "warn", "疑似"]:
        return "疑似"

    if lower in ["block", "blocked", "reject", "rejected", "illegal", "risk", "违规"]:
        return "违规"

    return None


def parse_status(api_result):
    """
    兼容 text/audio/video 三类接口的不同返回结构。
    """
    if not api_result.get("ok"):
        return "未知"

    obj = api_result.get("response_json") or {}

    direct_paths = [
        ["data", "upstream_response", "data", "content_category"],
        ["data", "text_detection", "data", "content_category"],
        ["data", "content_category"],
        ["data", "suggestion"],
        ["data", "conclusion"],
        ["data", "result", "suggestion"],
        ["data", "result", "conclusion"],
        ["data", "upstream_response", "data", "suggestion"],
        ["data", "upstream_response", "data", "conclusion"],
    ]

    for path in direct_paths:
        cur = obj
        ok = True
        for key in path:
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if ok:
            status = normalize_status(cur)
            if status:
                return status

    for k, v in iter_values(obj):
        if k in [
            "content_category",
            "suggestion",
            "conclusion",
            "risk_level",
            "riskLevel",
            "status"
        ]:
            status = normalize_status(v)
            if status:
                return status

    return "合规" if api_result.get("http_status") == 200 else "未知"


def extract_risk_info(api_result):
    obj = api_result.get("response_json") or {}

    labels = []
    risk_words = []
    max_confidence = None

    for k, v in iter_values(obj):
        if k in ["label", "category", "risk_label", "riskLabel", "type"]:
            if isinstance(v, str) and v and v not in labels:
                labels.append(v)

        if k in ["risk_words", "riskWords", "risk_word", "riskWord", "keywords", "keyword"]:
            if isinstance(v, list):
                for item in v:
                    item = str(item)
                    if item and item not in risk_words:
                        risk_words.append(item)
            elif isinstance(v, str):
                if v and v not in risk_words:
                    risk_words.append(v)

        if k in ["confidence", "score", "prob", "probability"]:
            if isinstance(v, (int, float)):
                max_confidence = v if max_confidence is None else max(max_confidence, v)

    return {
        "labels": labels,
        "risk_words": risk_words,
        "max_confidence": max_confidence
    }


def merge_status(statuses):
    values = [s for s in statuses if s]

    if "违规" in values:
        return "违规"
    if "疑似" in values:
        return "疑似"
    if "未知" in values and len(set(values)) == 1:
        return "未知"
    if "合规" in values:
        return "合规"

    return "未知"


def should_skip_text(text_path: Path):
    if not text_path.exists():
        return True, "文本不存在"

    content = text_path.read_text(encoding="utf-8", errors="ignore").strip()

    if not content:
        return True, "空文本"

    if "未启用语音转写" in content:
        return True, "占位文本"

    return False, content


def audit_segment(account_dir: Path, segment_id: str, config: dict):
    audit_dir = account_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)

    out_file = audit_dir / f"{segment_id}.all.audit.json"

    if out_file.exists():
        return False

    video_path = account_dir / "video" / f"{segment_id}.mp4"
    audio_path = account_dir / "audio" / f"{segment_id}.wav"
    text_path = account_dir / "text" / f"{segment_id}.txt"

    if not video_path.exists():
        print(f"[WAIT] {segment_id} 视频不存在: {video_path}", flush=True)
        return False

    if not audio_path.exists():
        print(f"[WAIT] {segment_id} 音频不存在: {audio_path}", flush=True)
        return False

    skip_text, text_content = should_skip_text(text_path)
    if skip_text:
        print(f"[WAIT] {segment_id} 文本不可检测: {text_content}", flush=True)
        return False

    base_url = config.get("base_url", "http://localhost:8080").rstrip("/")
    timeout = int(config.get("timeout", 300))
    text_max_chars = int(config.get("text_max_chars", 10000))

    print("=" * 80, flush=True)
    print(f"[AUDIT_ALL] source={account_dir.name}, segment={segment_id}", flush=True)
    print(f"[VIDEO] {video_path}", flush=True)
    print(f"[AUDIO] {audio_path}", flush=True)
    print(f"[TEXT]  {text_path}", flush=True)

    raw_results = {}
    modality_status = {}
    all_labels = []
    all_risk_words = []
    max_confidence = None

    # 1. 视频检测
    print(f"[REQUEST] video -> {base_url}/api/v1/detect/video", flush=True)
    video_result = multipart_upload(
        base_url + "/api/v1/detect/video",
        video_path,
        timeout=timeout
    )

    # 有些视频接口可能需要 check_list，失败时尝试补一次
    if not video_result.get("ok") and video_result.get("http_status") in [400, 422]:
        print("[RETRY] video with check_list=all", flush=True)
        video_result = multipart_upload(
            base_url + "/api/v1/detect/video",
            video_path,
            timeout=timeout,
            fields={"check_list": "all"}
        )

    raw_results["video"] = video_result
    modality_status["video"] = parse_status(video_result)

    # 2. 音频检测
    print(f"[REQUEST] audio -> {base_url}/api/v1/detect/audio", flush=True)
    audio_result = multipart_upload(
        base_url + "/api/v1/detect/audio",
        audio_path,
        timeout=timeout
    )
    raw_results["audio"] = audio_result
    modality_status["audio"] = parse_status(audio_result)

    # 3. 文本检测
    print(f"[REQUEST] text -> {base_url}/api/v1/detect/text", flush=True)

    text_chunks = [
        text_content[i:i + text_max_chars]
        for i in range(0, len(text_content), text_max_chars)
    ]

    text_chunk_results = []
    text_statuses = []

    for idx, chunk in enumerate(text_chunks, 1):
        print(f"[REQUEST] text chunk {idx}/{len(text_chunks)}", flush=True)
        r = post_json(
            base_url + "/api/v1/detect/text",
            {"content": chunk},
            timeout=timeout
        )
        text_chunk_results.append({
            "chunk_index": idx,
            "chunk_length": len(chunk),
            "result": r
        })
        text_statuses.append(parse_status(r))

    text_result = {
        "ok": all(x["result"].get("ok") for x in text_chunk_results),
        "chunks": text_chunk_results
    }

    raw_results["text"] = text_result
    modality_status["text"] = merge_status(text_statuses)

    # 汇总风险信息
    for key, r in raw_results.items():
        if key == "text":
            for chunk in r.get("chunks", []):
                info = extract_risk_info(chunk.get("result", {}))
                for label in info["labels"]:
                    if label not in all_labels:
                        all_labels.append(label)
                for word in info["risk_words"]:
                    if word not in all_risk_words:
                        all_risk_words.append(word)
                conf = info["max_confidence"]
                if isinstance(conf, (int, float)):
                    max_confidence = conf if max_confidence is None else max(max_confidence, conf)
        else:
            info = extract_risk_info(r)
            for label in info["labels"]:
                if label not in all_labels:
                    all_labels.append(label)
            for word in info["risk_words"]:
                if word not in all_risk_words:
                    all_risk_words.append(word)
            conf = info["max_confidence"]
            if isinstance(conf, (int, float)):
                max_confidence = conf if max_confidence is None else max(max_confidence, conf)

    final_status = merge_status([
        modality_status.get("video"),
        modality_status.get("audio"),
        modality_status.get("text"),
    ])

    output = {
        "audit_type": "all",
        "audit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": account_dir.name,
        "segment_id": segment_id,
        "status": final_status,
        "modality_status": modality_status,
        "labels": all_labels,
        "risk_words": all_risk_words,
        "max_confidence": max_confidence,
        "paths": {
            "video": str(video_path),
            "audio": str(audio_path),
            "text": str(text_path),
        },
        "raw_results": raw_results
    }

    out_file.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"[OK] {out_file} => {final_status} | {modality_status}", flush=True)
    return True


def find_segment_ids(account_dir: Path):
    ids = set()

    for p in (account_dir / "video").glob("*.mp4"):
        ids.add(p.stem)

    for p in (account_dir / "audio").glob("*.wav"):
        ids.add(p.stem)

    for p in (account_dir / "text").glob("*.txt"):
        ids.add(p.stem)

    return sorted(ids)


def scan_once():
    config = load_config()

    if not config.get("enabled", True):
        print("[DISABLED] audit_config.json enabled=false", flush=True)
        return 0

    if not OUTPUT_ROOT.exists():
        print(f"[WARN] output 不存在: {OUTPUT_ROOT}", flush=True)
        return 0

    count = 0

    for account_dir in sorted(OUTPUT_ROOT.iterdir()):
        if not account_dir.is_dir():
            continue

        for segment_id in find_segment_ids(account_dir):
            try:
                if audit_segment(account_dir, segment_id, config):
                    count += 1
            except Exception as e:
                print(f"[FAIL] {account_dir.name}/{segment_id}: {repr(e)}", flush=True)

    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=int, default=30)
    args = parser.parse_args()

    print("=" * 80, flush=True)
    print("[MULTI-MODAL AUDIT LOOP START]", flush=True)
    print(f"OUTPUT_ROOT: {OUTPUT_ROOT}", flush=True)
    print(f"CONFIG_FILE: {CONFIG_FILE}", flush=True)
    print("检测类型: video + audio + text", flush=True)
    print("=" * 80, flush=True)

    while True:
        count = scan_once()
        print(f"[SCAN_DONE] 新增综合审核: {count}", flush=True)

        if not args.loop:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
