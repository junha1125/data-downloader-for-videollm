import json
import os
import sys
import argparse
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import numpy as np


def get_video_duration(video_path, timeout=10):
    """Get video duration in seconds using ffprobe with timeout."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True, text=True, timeout=timeout
        )
        duration = float(result.stdout.strip())
        return duration
    except (subprocess.TimeoutExpired, ValueError, Exception) as e:
        print(f"[WARNING] ffprobe failed for {video_path}: {e}")
        return None


def is_video_valid(video_path, timeout=60):
    """Check if video is readable by decord, with a hard timeout.

    Runs decord in a subprocess so it can be killed if it hangs.
    Exit code 0 = valid, anything else = invalid.
    """
    try:
        result = subprocess.run(
            [
                sys.executable, "-c",
                "import sys; from decord import VideoReader; "
                "vr = VideoReader(sys.argv[1]); vr[0]; print('OK')",
                video_path,
            ],
            capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode == 0 and "OK" in result.stdout
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] decord hung for {timeout}s: {video_path}")
        return False
    except Exception as e:
        print(f"[WARNING] decord validation failed for {video_path}: {e}")
        return False


def process_chunk(chunk, video_base_dir, thread_idx, ffprobe_timeout, decord_timeout, output_dir):
    """Process a chunk and save results to a per-thread JSONL file immediately upon completion."""
    results = []
    durations = []
    total = len(chunk)
    for i, data in enumerate(chunk):
        video_rel_path = data.get("video", "")
        video_path = os.path.join(video_base_dir, video_rel_path)

        # EpicKitchens 폴더 영상은 무조건 스킵
        if "EpicKitchens" in video_rel_path:
            print(f"  [Thread {thread_idx}] [SKIP] EpicKitchens -> {video_rel_path}")
            if (i + 1) % 100 == 0 or (i + 1) == total:
                print(f"  [Thread {thread_idx}] {i + 1}/{total} ({(i + 1) / total * 100:.1f}%)")
            continue

        # Step 1: get duration via ffprobe (fast, with timeout)
        duration = get_video_duration(video_path, timeout=ffprobe_timeout)
        if duration is None:
            if (i + 1) % 100 == 0 or (i + 1) == total:
                print(f"  [Thread {thread_idx}] {i + 1}/{total} ({(i + 1) / total * 100:.1f}%)")
            continue

        # Step 2: validate with decord (with timeout — won't hang forever)
        if not is_video_valid(video_path, timeout=decord_timeout):
            if (i + 1) % 100 == 0 or (i + 1) == total:
                print(f"  [Thread {thread_idx}] {i + 1}/{total} ({(i + 1) / total * 100:.1f}%)")
            continue

        data["video_duration"] = duration
        results.append(data)
        durations.append(duration)

        if (i + 1) % 100 == 0 or (i + 1) == total:
            print(f"  [Thread {thread_idx}] {i + 1}/{total} ({(i + 1) / total * 100:.1f}%)")

    # Save per-thread JSONL as soon as this thread finishes
    thread_output_path = os.path.join(output_dir, f"thread_{thread_idx:04d}.jsonl")
    with open(thread_output_path, "w") as f:
        for data in results:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    print(f"  [Thread {thread_idx}] Saved {len(results)} entries -> {thread_output_path}")

    return results, durations


def parse_args():
    parser = argparse.ArgumentParser(description="Add video duration to JSONL and draw a histogram.")
    parser.add_argument("--input", "-i", type=str, required=True,
                        help="Path to input JSONL file")
    parser.add_argument("--video-base-dir", "-v", type=str, required=True,
                        help="Base directory for video files (joined with 'video' field in JSONL)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Path to final merged output JSONL file (default: <input>_with_duration.jsonl)")
    parser.add_argument("--duration-dir", type=str, default="duration_json",
                        help="Directory to save per-thread JSONL files (default: duration_json)")
    parser.add_argument("--histogram", type=str, default="video_duration_histogram.png",
                        help="Path to save histogram PNG (default: video_duration_histogram.png)")
    parser.add_argument("--num-threads", "-t", type=int, default=16,
                        help="Number of threads (default: 16)")
    parser.add_argument("--bin-size", "-b", type=int, default=30,
                        help="Histogram bin size in seconds (default: 30)")
    parser.add_argument("--ffprobe-timeout", type=int, default=10,
                        help="Timeout in seconds for each ffprobe call (default: 10)")
    parser.add_argument("--decord-timeout", type=int, default=10,
                        help="Timeout in seconds for each decord validation call (default: 10)")
    return parser.parse_args()


def main():
    args = parse_args()

    input_jsonl = args.input
    video_base_dir = args.video_base_dir
    output_jsonl = args.output or input_jsonl.replace(".jsonl", "_with_duration.jsonl")
    duration_dir = args.duration_dir
    output_histogram = args.histogram
    num_threads = args.num_threads
    bin_size = args.bin_size
    ffprobe_timeout = args.ffprobe_timeout
    decord_timeout = args.decord_timeout

    # ---- Create duration_json directory ----
    os.makedirs(duration_dir, exist_ok=True)
    print(f"Per-thread JSONL files will be saved to: {duration_dir}/")

    # ---- Load JSONL ----
    print(f"Loading {input_jsonl} ...")
    with open(input_jsonl, "r") as f:
        all_data = [json.loads(line) for line in f if line.strip()]
    print(f"Loaded {len(all_data)} entries.")

    # ---- Split into chunks ----
    chunk_size = (len(all_data) + num_threads - 1) // num_threads
    chunks = [all_data[i:i + chunk_size] for i in range(0, len(all_data), chunk_size)]
    print(f"Split into {len(chunks)} chunks (chunk_size ~{chunk_size})")

    # ---- Process with ThreadPoolExecutor ----
    all_durations = []
    lock = threading.Lock()

    def worker(idx, chunk):
        # Skip if this thread's output already exists
        thread_output_path = os.path.join(duration_dir, f"thread_{idx:04d}.jsonl")
        if os.path.exists(thread_output_path):
            print(f"  [Thread {idx}] SKIP — {thread_output_path} already exists")
            # Still load durations for histogram
            with open(thread_output_path, "r") as f:
                for line in f:
                    if line.strip():
                        d = json.loads(line)
                        dur = d.get("video_duration")
                        if dur is not None:
                            with lock:
                                all_durations.append(dur)
            return

        results, durations = process_chunk(chunk, video_base_dir, idx, ffprobe_timeout, decord_timeout, duration_dir)
        with lock:
            all_durations.extend(durations)
        print(f"  [Thread {idx}] Done — {len(results)} entries, {len(durations)} valid durations")

    print(f"Processing videos with {num_threads} threads "
          f"(ffprobe timeout={ffprobe_timeout}s, decord timeout={decord_timeout}s) ...")
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for idx, chunk in enumerate(chunks):
            futures.append(executor.submit(worker, idx, chunk))
        for f in futures:
            f.result()

    # ---- Merge all per-thread JSONL files into final output (preserving order) ----
    print(f"\nMerging per-thread JSONL files from {duration_dir}/ -> {output_jsonl} ...")
    thread_files = sorted(
        [f for f in os.listdir(duration_dir) if f.startswith("thread_") and f.endswith(".jsonl")]
    )
    total_entries = 0
    with open(output_jsonl, "w") as fout:
        for tf in thread_files:
            tf_path = os.path.join(duration_dir, tf)
            with open(tf_path, "r") as fin:
                for line in fin:
                    if line.strip():
                        fout.write(line)
                        total_entries += 1
    print(f"Merged {total_entries} entries from {len(thread_files)} thread files -> {output_jsonl}")

    # ---- Draw histogram ----
    print(f"Drawing histogram with {len(all_durations)} durations ...")
    if all_durations:
        max_dur = max(all_durations)
        bins = np.arange(0, max_dur + bin_size, bin_size)

        plt.figure(figsize=(14, 6))
        plt.hist(all_durations, bins=bins, edgecolor="black", alpha=0.75)
        plt.xlabel("Video Duration (seconds)")
        plt.ylabel("Count")
        plt.title(f"Video Duration Distribution (N={len(all_durations)}, bin={bin_size}s)")
        plt.xticks(bins, rotation=45)
        plt.tight_layout()
        plt.savefig(output_histogram, dpi=150)
        plt.close()
        print(f"Histogram saved to {output_histogram}")
    else:
        print("No valid durations found — skipping histogram.")

    print("Done!")

if __name__ == "__main__":
    main()