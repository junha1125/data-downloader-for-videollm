import os
import re
import math
import subprocess
import sys
import argparse
from collections import defaultdict

# ============================================================
# Config (defaults)
# ============================================================
DEFAULT_REPO_ID = "nyu-visionx/Cambrian-S-3M"
DEFAULT_DOWNLOAD_DIR = "./cambrian_s_3m"
DEFAULT_EXCLUDE_PREFIXES = ["ego4dhcap"]
DEFAULT_SAMPLE_RATIO = 0.1  # 10% of _001+ files


def parse_args():
    parser = argparse.ArgumentParser(
        description="Cambrian-S-3M Selective Download Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download 10%% of data (default)
  python download_part_Cambrian-S-3M.py

  # Download 20%% of data
  python download_part_Cambrian-S-3M.py --sample-ratio 0.2

  # Download 100%% of data (includes ego4dhcap when >= 0.9)
  python download_part_Cambrian-S-3M.py --sample-ratio 1.0

  # Skip confirmation prompt
  python download_part_Cambrian-S-3M.py --sample-ratio 0.3 --yes

  # Custom download directory
  python download_part_Cambrian-S-3M.py --download-dir /path/to/data --sample-ratio 0.5
        """,
    )
    parser.add_argument(
        "--sample-ratio",
        type=float,
        default=DEFAULT_SAMPLE_RATIO,
        help=f"Ratio of files to download (0.0-1.0). Default: {DEFAULT_SAMPLE_RATIO}. "
        "When >= 0.9, ego4dhcap is automatically included.",
    )
    parser.add_argument(
        "--download-dir",
        type=str,
        default=DEFAULT_DOWNLOAD_DIR,
        help=f"Directory to download files. Default: {DEFAULT_DOWNLOAD_DIR}",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        nargs="*",
        default=None,
        help="Dataset prefixes to exclude. Default: ego4dhcap (auto-included when sample-ratio >= 0.9)",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )
    parser.add_argument(
        "--skip-decompress",
        action="store_true",
        help="Skip decompression step",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )

    args = parser.parse_args()

    # Validate sample ratio
    if not 0.0 < args.sample_ratio <= 1.0:
        parser.error("--sample-ratio must be between 0.0 (exclusive) and 1.0 (inclusive)")

    # Handle exclude prefixes based on sample ratio
    if args.exclude is not None:
        args.exclude_prefixes = args.exclude
    elif args.sample_ratio >= 0.9:
        # Auto-include ego4dhcap when sample ratio >= 0.9
        args.exclude_prefixes = []
        print(f"  Note: sample-ratio >= 0.9, including ego4dhcap dataset")
    else:
        args.exclude_prefixes = DEFAULT_EXCLUDE_PREFIXES

    return args


# ============================================================
# Progress Tracking
# ============================================================
class ProgressTracker:
    """Track completed downloads and extractions to enable incremental updates."""

    def __init__(self, download_dir):
        self.download_dir = download_dir
        self.progress_dir = os.path.join(download_dir, ".progress")
        self.downloaded_file = os.path.join(self.progress_dir, "downloaded.txt")
        self.extracted_file = os.path.join(self.progress_dir, "extracted.txt")

    def init(self):
        """Initialize progress tracking directory."""
        os.makedirs(self.progress_dir, exist_ok=True)

    def _load_set(self, filepath):
        """Load a set of filenames from a text file."""
        if not os.path.exists(filepath):
            return set()
        with open(filepath, "r") as f:
            return set(line.strip() for line in f if line.strip())

    def _save_set(self, filepath, items):
        """Save a set of filenames to a text file."""
        with open(filepath, "w") as f:
            for item in sorted(items):
                f.write(f"{item}\n")

    def _append_item(self, filepath, item):
        """Append a single item to a text file."""
        with open(filepath, "a") as f:
            f.write(f"{item}\n")

    def get_downloaded(self):
        """Get set of already downloaded files."""
        return self._load_set(self.downloaded_file)

    def get_extracted(self):
        """Get set of already extracted files."""
        return self._load_set(self.extracted_file)

    def mark_downloaded(self, filename):
        """Mark a file as downloaded."""
        self._append_item(self.downloaded_file, filename)

    def mark_extracted(self, filename):
        """Mark a file as extracted."""
        self._append_item(self.extracted_file, filename)

    def is_downloaded(self, filename):
        """Check if a file was already downloaded."""
        return filename in self.get_downloaded()

    def is_extracted(self, filename):
        """Check if a file was already extracted."""
        return filename in self.get_extracted()

    def get_stats(self):
        """Get progress statistics."""
        return {
            "downloaded": len(self.get_downloaded()),
            "extracted": len(self.get_extracted()),
        }


# ============================================================
# Step 0: Check dependencies
# ============================================================
def check_dependencies():
    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("huggingface_hub is not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub"])
        from huggingface_hub import HfApi

    if subprocess.call("which zstd", shell=True, stdout=subprocess.DEVNULL) != 0:
        print("Error: zstd is not installed. Please install it (e.g., apt-get install zstd).")
        sys.exit(1)

    return HfApi


# ============================================================
# Step 1: Fetch file list from repository
# ============================================================
def get_file_list(HfApi, repo_id):
    print("=" * 60)
    print("Step 1: Fetching file list...")
    print("=" * 60)

    api = HfApi()
    repo_info = api.list_repo_tree(
        repo_id=repo_id, repo_type="dataset", recursive=False
    )
    file_info = {}  # filename -> size_bytes
    for item in repo_info:
        if hasattr(item, "rfilename"):
            file_info[item.rfilename] = getattr(item, "size", 0) or 0

    files = list(file_info.keys())
    total_gb = sum(file_info.values()) / (1024**3)
    print(f"  Total files: {len(files)}")
    print(f"  Total size:  {total_gb:,.2f} GB ({total_gb / 1024:.2f} TB)")
    return files, file_info


# ============================================================
# Step 2 & 3: Select files to download
# ============================================================
def select_files_to_download(files, file_info, exclude_prefixes, sample_ratio, tracker):
    print("\n" + "=" * 60)
    print("Step 2 & 3: Selecting files to download...")
    print(f"  Sample ratio: {sample_ratio * 100:.0f}%")
    print(f"  Excluded: {exclude_prefixes if exclude_prefixes else '(none)'}")
    print("=" * 60)

    already_downloaded = tracker.get_downloaded()
    download_list = []
    skip_count = 0

    # Always download .jsonl files
    jsonl_files = [f for f in files if f.endswith(".jsonl")]
    for f in jsonl_files:
        if f in already_downloaded:
            skip_count += 1
        else:
            download_list.append(f)

    jsonl_size = sum(file_info.get(f, 0) for f in jsonl_files)
    jsonl_new = len([f for f in jsonl_files if f not in already_downloaded])
    print(f"\n  [JSONL] {len(jsonl_files)} files ({jsonl_size / (1024**3):.2f} GB), {jsonl_new} new")

    # Filter .tar.zst files only
    tar_files = [f for f in files if f.endswith(".tar.zst")]

    # Group by dataset name
    dataset_groups = defaultdict(list)
    for f in tar_files:
        basename = os.path.basename(f)
        name_without_ext = basename.replace(".tar.zst", "")
        match = re.match(r"^(.+?)_(\d+)$", name_without_ext)
        if match:
            dataset_name = match.group(1)
            part_num = int(match.group(2))
            dataset_groups[dataset_name].append((part_num, f))

    for name in dataset_groups:
        dataset_groups[name].sort(key=lambda x: x[0])

    print(f"\n  Dataset groups found: {len(dataset_groups)}")

    # Filter and select
    excluded_count = 0
    excluded_size = 0

    print(f"\n  {'Dataset':<28} {'Total':>6} {'Select':>6} {'New':>6} {'Down(GB)':>10} {'Total(GB)':>10}")
    print(f"  {'-'*76}")

    for dataset_name in sorted(dataset_groups.keys()):
        parts = dataset_groups[dataset_name]
        total_parts_size = sum(file_info.get(f, 0) for _, f in parts)

        # Check exclusion
        if dataset_name in exclude_prefixes:
            excluded_count += len(parts)
            excluded_size += total_parts_size
            print(
                f"  [SKIP] {dataset_name:<23} {len(parts):>6} {'--':>6} {'--':>6} "
                f"{'--':>10} {total_parts_size / (1024**3):>10.2f}"
            )
            continue

        # Add _000 files (always)
        zero_parts = [(num, f) for num, f in parts if num == 0]
        selected_parts = list(zero_parts)

        # Process _001+ files
        rest_parts = [(num, f) for num, f in parts if num > 0]

        if len(rest_parts) > 0:
            # Select sample_ratio sequentially (min 1)
            sample_size = max(1, math.ceil(len(rest_parts) * sample_ratio))
            selected_parts.extend(rest_parts[:sample_size])

        # Count new vs already downloaded
        new_files = []
        for num, f in selected_parts:
            if f in already_downloaded:
                skip_count += 1
            else:
                new_files.append(f)
                download_list.append(f)

        down_size = sum(file_info.get(f, 0) for _, f in selected_parts)
        selected_nums = [str(num).zfill(3) for num, _ in selected_parts if num > 0]
        suffix = f"  (+{', '.join(selected_nums[:5])}{'...' if len(selected_nums) > 5 else ''})" if selected_nums else ""

        print(
            f"  [  OK] {dataset_name:<23} {len(parts):>6} {len(selected_parts):>6} "
            f"{len(new_files):>6} {down_size / (1024**3):>10.2f} "
            f"{total_parts_size / (1024**3):>10.2f}{suffix}"
        )

    # Summary
    total_all_size = sum(file_info.get(f, 0) for f in files)
    download_size = sum(file_info.get(f, 0) for f in download_list)

    print(f"\n  {'='*76}")
    print(f"  Summary")
    print(f"  {'='*76}")
    print(f"  Total files:      {len(tar_files)} tar.zst + {len(jsonl_files)} jsonl")
    print(f"  Total size:       {total_all_size / (1024**3):,.2f} GB ({total_all_size / (1024**4):.2f} TB)")
    print(f"  Excluded:         {excluded_count} files ({excluded_size / (1024**3):,.2f} GB)")
    print(f"  Already done:     {skip_count} files (skipping)")
    print(f"  New to download:  {len(download_list)} files")
    print(f"  New download size:{download_size / (1024**3):,.2f} GB ({download_size / (1024**4):.2f} TB)")
    print(f"  {'='*76}")

    return download_list


# ============================================================
# Step 4: Download files
# ============================================================
def download_files(download_list, download_dir, repo_id, tracker, dry_run=False):
    from huggingface_hub import hf_hub_download

    print("\n" + "=" * 60)
    print("Step 4: Downloading...")
    print("=" * 60)

    if dry_run:
        print("  [DRY RUN] Would download:")
        for f in download_list:
            print(f"    - {f}")
        return []

    os.makedirs(download_dir, exist_ok=True)

    failed = []
    for i, filepath in enumerate(download_list, 1):
        print(f"\n  [{i}/{len(download_list)}] Downloading: {filepath}")
        try:
            hf_hub_download(
                repo_id=repo_id,
                filename=filepath,
                repo_type="dataset",
                local_dir=download_dir,
            )
            tracker.mark_downloaded(filepath)
            print(f"    [OK] Done")
        except Exception as e:
            print(f"    [FAIL] {e}")
            failed.append(filepath)

    if failed:
        print(f"\n  Failed downloads: {len(failed)}")
        for f in failed:
            print(f"    - {f}")
    else:
        print(f"\n  All {len(download_list)} files downloaded successfully!")

    return failed


# ============================================================
# Step 5: Decompress
# ============================================================
def decompress_files(download_dir, tracker, dry_run=False):
    """
    Decompress .tar.zst files.

    NOTE: Each .tar.zst file is an INDEPENDENT archive. They don't need to be
    processed in sequence (000, 001, 002...). You can decompress 004 alone
    without having 000-003. The numbering is just for organization, not for
    split archives.
    """
    print("\n" + "=" * 60)
    print("Step 5: Decompressing...")
    print("=" * 60)

    tar_files = [f for f in os.listdir(download_dir) if f.endswith(".tar.zst")]

    if not tar_files:
        print("  No .tar.zst files to decompress.")
        return

    # Filter out already extracted files
    already_extracted = tracker.get_extracted()
    to_extract = [f for f in tar_files if f not in already_extracted]

    print(f"  Total .tar.zst files: {len(tar_files)}")
    print(f"  Already extracted: {len(tar_files) - len(to_extract)}")
    print(f"  To extract: {len(to_extract)}")

    if not to_extract:
        print("  Nothing new to extract.")
        return

    if dry_run:
        print("  [DRY RUN] Would extract:")
        for f in sorted(to_extract):
            print(f"    - {f}")
        return

    for i, file in enumerate(sorted(to_extract), 1):
        name_without_ext = file.replace(".tar.zst", "")
        dir_name = re.sub(r"_\d+$", "", name_without_ext)
        target_dir = os.path.join(download_dir, dir_name)

        print(f"\n  [{i}/{len(to_extract)}] {file} -> {dir_name}/")

        os.makedirs(target_dir, exist_ok=True)

        filepath = os.path.join(download_dir, file)
        result = subprocess.run(
            ["tar", "-I", "zstd", "-xf", filepath, "-C", target_dir],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            tracker.mark_extracted(file)
            print(f"    [OK] Decompressed")
        else:
            print(f"    [FAIL] {result.stderr}")

    print("\n  Decompression complete!")


# ============================================================
# Main
# ============================================================
def main():
    args = parse_args()

    print("=" * 60)
    print("Cambrian-S-3M Selective Download Script")
    print("=" * 60)
    print(f"  Download dir:  {args.download_dir}")
    print(f"  Exclude:       {args.exclude_prefixes if args.exclude_prefixes else '(none)'}")
    print(f"  Sample ratio:  {args.sample_ratio * 100:.0f}%")
    if args.dry_run:
        print(f"  Mode:          DRY RUN (no actual download)")

    # Initialize progress tracker
    tracker = ProgressTracker(args.download_dir)
    tracker.init()

    stats = tracker.get_stats()
    print(f"\n  Progress: {stats['downloaded']} downloaded, {stats['extracted']} extracted")

    # Check dependencies
    HfApi = check_dependencies()

    # Step 1: File list
    files, file_info = get_file_list(HfApi, DEFAULT_REPO_ID)

    # Step 2 & 3: Select files
    download_list = select_files_to_download(
        files, file_info, args.exclude_prefixes, args.sample_ratio, tracker
    )

    if not download_list:
        print("\n  No new files to download!")
        if not args.skip_decompress:
            decompress_files(args.download_dir, tracker, args.dry_run)
        print("\n" + "=" * 60)
        print("All done!")
        print("=" * 60)
        return

    # Confirm before download
    download_size = sum(file_info.get(f, 0) for f in download_list)
    if not args.yes and not args.dry_run:
        response = input(
            f"\nDownload {len(download_list)} files ({download_size / (1024**3):,.2f} GB)? (y/n): "
        )
        if response.lower() != "y":
            print("Cancelled.")
            return

    # Step 4: Download
    failed = download_files(download_list, args.download_dir, DEFAULT_REPO_ID, tracker, args.dry_run)

    # Step 5: Decompress
    if not args.skip_decompress:
        decompress_files(args.download_dir, tracker, args.dry_run)

    print("\n" + "=" * 60)
    print("All done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
