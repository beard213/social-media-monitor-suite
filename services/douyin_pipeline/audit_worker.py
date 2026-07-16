import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT / "output" / "douyin_live_dataset"
CONFIG_FILE = ROOT / "audit_config.json"


def load_config():
    if not CONFIG_FILE.exists():
        return {
            "enabled": True,
            "base_url": "http://localhost:8080",
            "mode": "text",
            "interval_seconds": 30,
            "text_max_chars": 10000,
            "timeout": 120,
        }

    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def related_paths_from_text(text_path: Path):
    """
    text/20260709_xxxxxx.txt
    推导：
    video/20260709_xxxxxx.mp4
    audio/20260709_xxxxxx.wav
    metadata/20260709_xxxxxx.json
    audit/20260709_xxxxxx.audit.json
    """

    parts = list(text_path.parts)

    if "text" not in parts:
        raise ValueError(f"路径中找不到 text 目录: {text_path}")

    idx = parts.index("text")

    video_parts = parts.copy()
    audio_parts = parts.copy()
    metadata_parts = parts.copy()
    audit_parts = parts.copy()

    video_parts[idx] = "video"
    audio_parts[idx] = "audio"
    metadata_parts[idx] = "metadata"
    audit_parts[idx] = "audit"

    video_path = Path(*video_parts).with_suffix(".mp4")
    audio_path = Path(*audio_parts).with_suffix(".wav")
    metadata_path = Path(*metadata_parts).with_suffix(".json")
    audit_path = Path(*audit_parts).with_suffix(".audit.json")

    return video_path, audio_path, metadata_path, audit_path


def extract_account(text_path: Path):
    parts = list(text_path.parts)

    if "douyin_live_dataset" in parts:
        idx = parts.index("douyin_live_dataset")
        if idx + 1 < len(parts):
            return parts[idx + 1]

    return ""


def call_text_audit(base_url: str, content: str, timeout: int):
    url = base_url.rstrip("/") + "/api/v1/detect/text"

    response = requests.post(
        url,
        json={"content": content},
        timeout=timeout,
    )

    result = {
        "request_url": url,
        "http_status": response.status_code,
        "ok": response.ok,
        "response_text": response.text,
    }

    try:
        result["response_json"] = response.json()
    except Exception:
        result["response_json"] = None

    return result


def summarize_text_result(api_result):
    """
    从接口返回中提取简要审核结论。
    文档中的文本接口结构大致为：
    data.upstream_response.data.content_category
    data.upstream_response.data.content_result
    """

    summary = {
        "content_category": "",
        "labels": [],
        "max_confidence": None,
        "risk_words": [],
    }

    try:
        resp = api_result.get("response_json") or {}
        upstream = resp.get("data", {}).get("upstream_response", {})
        data = upstream.get("data", {})

        summary["content_category"] = data.get("content_category", "")

        results = data.get("content_result", []) or []

        max_conf = None
        labels = []
        risk_words = []

        for item in results:
            label = item.get("label")
            if label:
                labels.append(label)

            conf = item.get("confidence")
            if isinstance(conf, (int, float)):
                max_conf = conf if max_conf is None else max(max_conf, conf)

            for w in item.get("risk_words", []) or []:
                if w not in risk_words:
                    risk_words.append(w)

            for sub in item.get("sub_result", []) or []:
                sub_label = sub.get("label")
                if sub_label:
                    labels.append(sub_label)

                sub_conf = sub.get("confidence")
                if isinstance(sub_conf, (int, float)):
                    max_conf = sub_conf if max_conf is None else max(max_conf, sub_conf)

                for w in sub.get("risk_words", []) or []:
                    if w not in risk_words:
                        risk_words.append(w)

        summary["labels"] = list(dict.fromkeys(labels))
        summary["max_confidence"] = max_conf
        summary["risk_words"] = risk_words

    except Exception as e:
        summary["parse_error"] = repr(e)

    return summary


def audit_one_text(text_path: Path, config: dict):
    text_path = text_path.resolve()

    video_path, audio_path, metadata_path, audit_path = related_paths_from_text(text_path)

    if audit_path.exists():
        print(f"[SKIP] 已审核: {audit_path}")
        return False

    text = text_path.read_text(encoding="utf-8", errors="ignore").strip()

    if not text:
        print(f"[SKIP] 空文本: {text_path}")
        return False

    max_chars = int(config.get("text_max_chars", 10000))
    timeout = int(config.get("timeout", 120))
    base_url = config.get("base_url", "http://localhost:8080")

    # 文档限制文本 10000 字符；超过则分块请求
    chunks = [
        text[i:i + max_chars]
        for i in range(0, len(text), max_chars)
    ]

    metadata = {}
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            metadata = {}

    api_results = []

    print(f"[AUDIT] {text_path}")
    print(f"[INFO] 文本长度: {len(text)}，分块数: {len(chunks)}")

    for idx, chunk in enumerate(chunks, 1):
        print(f"[REQUEST] text chunk {idx}/{len(chunks)}")

        try:
            result = call_text_audit(
                base_url=base_url,
                content=chunk,
                timeout=timeout,
            )
        except Exception as e:
            result = {
                "ok": False,
                "error": repr(e),
            }

        api_results.append(
            {
                "chunk_index": idx,
                "chunk_length": len(chunk),
                "result": result,
                "summary": summarize_text_result(result),
            }
        )

    final_categories = []
    final_labels = []
    final_risk_words = []
    max_confidence = None

    for item in api_results:
        summary = item.get("summary", {})

        category = summary.get("content_category")
        if category:
            final_categories.append(category)

        for label in summary.get("labels", []) or []:
            if label not in final_labels:
                final_labels.append(label)

        for w in summary.get("risk_words", []) or []:
            if w not in final_risk_words:
                final_risk_words.append(w)

        conf = summary.get("max_confidence")
        if isinstance(conf, (int, float)):
            max_confidence = conf if max_confidence is None else max(max_confidence, conf)

    if "违规" in final_categories:
        final_status = "违规"
    elif "疑似" in final_categories:
        final_status = "疑似"
    elif "合规" in final_categories:
        final_status = "合规"
    else:
        final_status = "未知"

    output = {
        "audit_type": "text",
        "audit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": extract_account(text_path),
        "segment_id": text_path.stem,
        "status": final_status,
        "labels": final_labels,
        "risk_words": final_risk_words,
        "max_confidence": max_confidence,
        "paths": {
            "text": str(text_path),
            "video": str(video_path) if video_path.exists() else "",
            "audio": str(audio_path) if audio_path.exists() else "",
            "metadata": str(metadata_path) if metadata_path.exists() else "",
        },
        "metadata": metadata,
        "api_results": api_results,
    }

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[OK] 审核结果保存: {audit_path}")
    print(f"[RESULT] {final_status}, labels={final_labels}, confidence={max_confidence}")

    return True


def scan_once(config):
    if not OUTPUT_ROOT.exists():
        print(f"[WARN] output 不存在: {OUTPUT_ROOT}")
        return 0

    txt_files = sorted(OUTPUT_ROOT.glob("*/text/*.txt"))

    count = 0

    for text_path in txt_files:
        try:
            ok = audit_one_text(text_path, config)
            if ok:
                count += 1
        except Exception as e:
            print(f"[FAIL] {text_path}: {repr(e)}")

    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
        help="只扫描一次，然后退出",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="循环扫描间隔秒数，默认读取 audit_config.json",
    )
    args = parser.parse_args()

    config = load_config()

    if not config.get("enabled", True):
        print("[AUDIT_DISABLED] audit_config.json 中 enabled=false")
        return

    interval = args.interval
    if interval is None:
        interval = int(config.get("interval_seconds", 30))

    print("=" * 80)
    print("[AUDIT WORKER START]")
    print(f"OUTPUT_ROOT: {OUTPUT_ROOT}")
    print(f"BASE_URL: {config.get('base_url')}")
    print(f"MODE: {config.get('mode')}")
    print(f"INTERVAL: {interval}")
    print("=" * 80)

    while True:
        count = scan_once(config)
        print(f"[SCAN_DONE] 本轮新增审核: {count}")

        if args.once:
            break

        time.sleep(interval)


if __name__ == "__main__":
    main()
