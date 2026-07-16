import argparse
import json
from pathlib import Path

import torch
from funasr import AutoModel


def extract_text(res):
    """兼容 FunASR 不同返回格式，尽量提取 text 字段。"""
    if isinstance(res, list):
        texts = []
        for item in res:
            if isinstance(item, dict):
                if "text" in item:
                    texts.append(item["text"])
                elif "sentence_info" in item:
                    for s in item["sentence_info"]:
                        if isinstance(s, dict) and "text" in s:
                            texts.append(s["text"])
            elif isinstance(item, str):
                texts.append(item)
        return "\n".join([t for t in texts if t]).strip()

    if isinstance(res, dict):
        if "text" in res:
            return str(res["text"]).strip()
        if "sentence_info" in res:
            return "\n".join(
                s.get("text", "") for s in res["sentence_info"] if isinstance(s, dict)
            ).strip()

    return str(res).strip()


def audio_to_text_path(audio_path: Path) -> Path:
    parts = list(audio_path.parts)
    if "audio" in parts:
        idx = parts.index("audio")
        parts[idx] = "text"
        return Path(*parts).with_suffix(".txt")
    return audio_path.with_suffix(".txt")


def audio_to_json_path(audio_path: Path) -> Path:
    parts = list(audio_path.parts)
    if "audio" in parts:
        idx = parts.index("audio")
        parts[idx] = "metadata"
        return Path(*parts).with_suffix(".funasr.json")
    return audio_path.with_suffix(".funasr.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        required=True,
        help="单个 wav 文件，或包含 wav 的目录，例如 output/douyin_live_dataset/account1/audio",
    )
    parser.add_argument(
        "--device",
        default="cuda:0" if torch.cuda.is_available() else "cpu",
        help="cuda:0 或 cpu",
    )
    args = parser.parse_args()

    input_path = Path(args.input)

    if input_path.is_file():
        wav_files = [input_path]
    else:
        wav_files = sorted(input_path.rglob("*.wav"))

    if not wav_files:
        print(f"[ERROR] 没找到 wav 文件: {input_path}")
        return

    print(f"[INFO] device = {args.device}")
    print(f"[INFO] wav 数量 = {len(wav_files)}")

    print("[INFO] 正在加载 FunASR 模型，第一次运行会下载模型，可能较慢...")
    model = AutoModel(
        model="paraformer-zh",
        vad_model="fsmn-vad",
        punc_model="ct-punc",
        device=args.device,
    )

    for wav in wav_files:
        print(f"\n[ASR] {wav}")
        try:
            res = model.generate(
                input=str(wav),
                batch_size_s=300,
            )

            text = extract_text(res)
            text_path = audio_to_text_path(wav)
            json_path = audio_to_json_path(wav)

            text_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.parent.mkdir(parents=True, exist_ok=True)

            text_path.write_text(text + "\n", encoding="utf-8")
            json_path.write_text(
                json.dumps(res, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            print(f"[OK] 文本保存: {text_path}")
            print(f"[OK] 结果保存: {json_path}")
            print("[TEXT_PREVIEW]")
            print(text[:300])

        except Exception as e:
            print(f"[FAIL] {wav}")
            print(repr(e))


if __name__ == "__main__":
    main()
