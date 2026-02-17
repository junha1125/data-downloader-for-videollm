import argparse
import json
import os
import subprocess

from tqdm import tqdm


def get_duration(video_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path],
            capture_output=True, text=True, timeout=10
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Filter out videos <= 5 seconds from JSONL")
    parser.add_argument("jsonl", help="Input JSONL file path")
    parser.add_argument("--video-root", default=".", help="Root directory where video files are stored")
    parser.add_argument("--output", default="cambrian_s_3m_filtered_over5s.jsonl", help="Output JSONL file")
    args = parser.parse_args()

    total = 0
    kept = 0
    skipped = 0
    error = 0

    with open(args.jsonl, "r") as fin, open(args.output, "w") as fout:
        for line in tqdm(fin, desc="Processing videos"):
            line = line.strip()
            if not line:
                continue
            total += 1
            data = json.loads(line)
            video_rel = data.get("video", "")
            video_path = os.path.join(args.video_root, video_rel)

            duration = get_duration(video_path)
            if duration is None:
                # 파일을 못 읽으면 일단 유지
                # fout.write(json.dumps(data, ensure_ascii=False) + "\n")
                # kept += 1
                error += 1
            elif duration >= 5.0:
                fout.write(json.dumps(data, ensure_ascii=False) + "\n")
                kept += 1
            else:
                skipped += 1

            if total % 10000 == 0:
                print(f"Processed {total} | kept {kept} | skipped {skipped} | error {error}")

    print(f"Done. Total: {total} | Kept: {kept} | Skipped(<5s): {skipped} | Error(kept): {error}")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()