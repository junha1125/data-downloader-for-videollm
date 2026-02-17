import argparse
import json
import os
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager

"""
python filter_short_videos.py cambrian_s_3m_filtered.jsonl --output cambrian_s_3m_filtered_over5s.jsonl
"""


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


def process_chunk(chunk_id, lines, video_root):
    """각 청크를 처리하고 결과를 반환"""
    kept = []
    skipped = 0
    error = 0
    total = len(lines)

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        data = json.loads(line)
        video_rel = data.get("video", "")
        video_path = os.path.join(video_root, video_rel)

        duration = get_duration(video_path)
        if duration is None:
            error += 1
        elif duration >= 5.0:
            kept.append(json.dumps(data, ensure_ascii=False))
        else:
            skipped += 1

        if (i + 1) % 10000 == 0:
            print(f"[Chunk {chunk_id:2d}] {i+1}/{total} | kept {len(kept)} | skipped {skipped} | error {error}")

    print(f"[Chunk {chunk_id:2d}] DONE {total}/{total} | kept {len(kept)} | skipped {skipped} | error {error}")
    return chunk_id, kept, skipped, error


def main():
    parser = argparse.ArgumentParser(description="Filter out videos <= 5 seconds from JSONL (parallel)")
    parser.add_argument("jsonl", help="Input JSONL file path")
    parser.add_argument("--video-root", default=".", help="Root directory where video files are stored")
    parser.add_argument("--output", default="cambrian_s_3m_filtered_over5s.jsonl", help="Output JSONL file")
    parser.add_argument("--workers", type=int, default=12, help="Number of parallel workers")
    args = parser.parse_args()

    # 1. 전체 데이터 로드
    print(f"Loading {args.jsonl} ...")
    t0 = time.time()
    with open(args.jsonl, "r") as f:
        all_lines = f.readlines()
    total_lines = len(all_lines)
    print(f"Loaded {total_lines:,} lines in {time.time()-t0:.1f}s")

    # 2. N등분
    n = args.workers
    chunk_size = (total_lines + n - 1) // n
    chunks = []
    for i in range(n):
        start = i * chunk_size
        end = min(start + chunk_size, total_lines)
        chunks.append(all_lines[start:end])
    print(f"Split into {n} chunks (each ~{chunk_size:,} lines)")

    # 메모리 절약: 원본 리스트 해제
    del all_lines

    # 3. 병렬 처리
    print(f"Starting {n} workers ...")
    t1 = time.time()
    results = [None] * n

    with ProcessPoolExecutor(max_workers=n) as executor:
        futures = {
            executor.submit(process_chunk, i, chunks[i], args.video_root): i
            for i in range(n)
        }
        for future in as_completed(futures):
            chunk_id, kept, skipped, error = future.result()
            results[chunk_id] = (kept, skipped, error)

    elapsed = time.time() - t1
    print(f"\nAll workers finished in {elapsed/60:.1f} min ({elapsed:.0f}s)")

    # 4. 결과 합치기 & 저장
    print(f"Merging results and writing to {args.output} ...")
    total_kept = 0
    total_skipped = 0
    total_error = 0

    with open(args.output, "w") as fout:
        for chunk_id, (kept, skipped, error) in enumerate(results):
            for line in kept:
                fout.write(line + "\n")
            total_kept += len(kept)
            total_skipped += skipped
            total_error += error

    total_elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"Total lines : {total_lines:,}")
    print(f"Kept (>=5s)  : {total_kept:,}")
    print(f"Skipped (<5s): {total_skipped:,}")
    print(f"Error        : {total_error:,}")
    print(f"Total time   : {total_elapsed/60:.1f} min")
    print(f"Saved to {args.output}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()