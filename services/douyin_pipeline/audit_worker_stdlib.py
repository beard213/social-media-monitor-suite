import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT / "output" / "douyin_live_dataset"
CONFIG_FILE = ROOT / "audit_config.json"


def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))

    return {
        "enabled": True,
        "base_url": "http://localhost:8080",
        "text_max_chars": 10000,
        "timeout": 120
    }


def post_json(url, payload, timeout):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="ignore")
            return {
                "ok": True,
                "http_status": resp.status,
                "response_text": text,
                "response_json": json.loads(text)
            }
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="ignore")
        return {
            "ok": False,
            "http_status": e.code,
            "response_text": text,
            "response_json": None
        }
    except Exception as e:
        return {
            "ok": False,
            "error": repr(e),
            "response_json": None
        }


def parse_summary(result):
    summary = {
        "content_category": "未知",
        "labels": [],
        "risk_words": [],
        "max_confidence": None
    }

    try:
        resp = result.get("response_json") or {}
        upstream = resp.get("data", {}).get("upstream_response", {})
        data = upstream.get("data", {})

        category = data.get("content_category")
        if category:
            summary["content_category"] = category

        labels = []
        risk_words = []
        max_conf = None

        for item in data.get("content_result", []) or []:
            if item.get("label"):
                labels.append(item["label"])

            conf = item.get("confidence")
            if isinstance(conf, (int, float)):
                max_conf = conf if max_conf is None else max(max_conf, conf)

            for w in item.get("risk_words", []) or []:
                if w not in risk_words:
                    risk_words.append(w)

            for sub in item.get("sub_result", []) or []:
                if sub.get("label"):
                    labels.append(sub["label"])

                sub_conf = sub.get("confidence")
                if isinstance(sub_conf, (int, float)):
                    max_conf = sub_conf if max_conf is None else max(max_conf, sub_conf)

                for w in sub.get("risk_words", []) or []:
                    if w not in risk_words:
                        risk_words.append(w)

        summary["labels"] = list(dict.fromkeys(labels))
        summary["risk_words"] = risk_words
        summary["max_confidence"] = max_conf

    except Exception as e:
        summary["parse_error"] = repr(e)

    return summary


def audit_text_file(text_path, config):
    text = text_path.read_text(encoding="utf-8", errors="ignore").strip()

    if not text:
        print(f"[SKIP] 空文本: {text_path}")
        return False

    account = text_path.parent.parent.name
    segment_id = text_path.stem
    audit_dir = text_path.parent.parent / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / f"{segment_id}.audit.json"

    if audit_path.exists():
        print(f"[SKIP] 已存在: {audit_path}")
        return False

    base_url = config.get("base_url", "http://localhost:8080").rstrip("/")
    url = base_url + "/api/v1/detect/text"
    timeout = int(config.get("timeout", 120))
    max_chars = int(config.get("text_max_chars", 10000))

    chunks = [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

    print(f"[AUDIT] {text_path}")
    print(f"[INFO] 文本长度={len(text)}, 分块数={len(chunks)}")

    api_results = []

    for idx, chunk in enumerate(chunks, 1):
        print(f"[REQUEST] chunk {idx}/{len(chunks)} -> {url}")
        result = post_json(url, {"content": chunk}, timeout)
        summary = parse_summary(result)

        api_results.append({
            "chunk_index": idx,
            "chunk_length": len(chunk),
            "result": result,
            "summary": summary
        })

    categories = []
    labels = []
    risk_words = []
    max_confidence = None

    for item in api_results:
        s = item.get("summary", {})

        cat = s.get("content_category")
        if cat:
            categories.append(cat)

        for label in s.get("labels", []) or []:
            if label not in labels:
                labels.append(label)

        for w in s.get("risk_words", []) or []:
            if w not in risk_words:
                risk_words.append(w)

        conf = s.get("max_confidence")
        if isinstance(conf, (int, float)):
            max_confidence = conf if max_confidence is None else max(max_confidence, conf)

    if "违规" in categories:
        final_status = "违规"
    elif "疑似" in categories:
        final_status = "疑似"
    elif "合规" in categories:
        final_status = "合规"
    else:
        final_status = "未知"

    output = {
        "audit_type": "text",
        "audit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": account,
        "segment_id": segment_id,
        "status": final_status,
        "labels": labels,
        "risk_words": risk_words,
        "max_confidence": max_confidence,
        "paths": {
            "text": str(text_path)
        },
        "api_results": api_results
    }

    audit_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"[OK] 审核结果保存: {audit_path}")
    print(f"[RESULT] {final_status}, labels={labels}, confidence={max_confidence}")

    return True


def main():
    config = load_config()

    if not config.get("enabled", True):
        print("[DISABLED] audit_config.json enabled=false")
        return

    text_files = sorted(OUTPUT_ROOT.glob("*/text/*.txt"))

    if not text_files:
        print(f"[WARN] 没有找到文本文件: {OUTPUT_ROOT}/*/text/*.txt")
        return

    count = 0

    for text_path in text_files:
        try:
            if audit_text_file(text_path, config):
                count += 1
        except Exception as e:
            print(f"[FAIL] {text_path}: {repr(e)}")

    print(f"[DONE] 新增审核结果: {count}")


if __name__ == "__main__":
    main()
