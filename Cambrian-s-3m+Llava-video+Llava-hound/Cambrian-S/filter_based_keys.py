import argparse
import json

"""
python filter_based_keys.py cambrian_s_3m_filtered_over5s.jsonl --output cambrian_s_3m_filtered_over5s_video.jsonl
"""


def should_exclude(data):
    # 1. "audio" key 존재
    if "audio" in data:
        return True

    # 2. "image" key 존재하고 "video" key 없음
    if "image" in data and "video" not in data:
        return True

    # 3. conversations human 부분에 <speech> 포함
    convs = data.get("conversations", [])
    for turn in convs:
        if turn.get("from") == "human" and "<speech>" in turn.get("value", ""):
            return True

    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", help="Input JSONL file")
    parser.add_argument("--output", default="cambrian_s_3m_filtered_over5s_video.jsonl")
    args = parser.parse_args()

    total = 0
    kept = 0
    excluded_audio = 0
    excluded_speech = 0
    excluded_image = 0

    with open(args.jsonl, "r") as fin, open(args.output, "w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            total += 1
            data = json.loads(line)

            if "audio" in data:
                excluded_audio += 1
                continue

            if "image" in data and "video" not in data:
                excluded_image += 1
                continue

            convs = data.get("conversations", [])
            has_speech = any(
                t.get("from") == "human" and "<speech>" in t.get("value", "")
                for t in convs
            )
            if has_speech:
                excluded_speech += 1
                continue

            fout.write(json.dumps(data, ensure_ascii=False) + "\n")
            kept += 1

            if total % 500000 == 0:
                print(f"Processed {total:,} | kept {kept:,}")

    print(f"\n{'='*50}")
    print(f"Total:              {total:,}")
    print(f"Kept:               {kept:,}")
    print(f"Excluded (audio):   {excluded_audio:,}")
    print(f"Excluded (speech):  {excluded_speech:,}")
    print(f"Excluded (image):   {excluded_image:,}")
    print(f"Excluded total:     {total - kept:,}")
    print(f"Saved to {args.output}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()