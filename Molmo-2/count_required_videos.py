import datasets
from collections import defaultdict

DATASETS = [
    "allenai/Molmo2-VideoCapQA",
    "allenai/Molmo2-VideoSubtitleQA",
    "allenai/Molmo2-AskModelAnything",
    "allenai/Molmo2-Cap",
]

# MB per video estimates
SIZE_ESTIMATES = {
    "conservative": 5,   # 5 MB
    "average": 10,       # 10 MB
    "generous": 20,      # 20 MB
}


def get_video_ids_from_dataset(dataset_name):
    """Load dataset and extract unique video IDs."""
    print(f"\n{'='*60}")
    print(f"Loading: {dataset_name}")
    print("="*60)

    video_ids = set()
    total_samples = 0

    try:
        # Get available splits
        ds_builder = datasets.load_dataset_builder(dataset_name)
        available_splits = list(ds_builder.info.splits.keys())
        print(f"Available splits: {available_splits}")

        for split in available_splits:
            print(f"  Loading split: {split}...")
            ds = datasets.load_dataset(dataset_name, split=split)
            total_samples += len(ds)

            # Find video_id column (might have different names)
            columns = ds.column_names
            video_col = None
            for col in ["video_id", "video", "vid_id", "id"]:
                if col in columns:
                    video_col = col
                    break

            if video_col:
                split_ids = set(ds[video_col])
                video_ids.update(split_ids)
                print(f"    Samples: {len(ds)}, Unique videos: {len(split_ids)}")
            else:
                print(f"    Columns: {columns}")
                print(f"    WARNING: No video_id column found!")

    except Exception as e:
        print(f"  ERROR: {e}")

    return video_ids, total_samples


def main():
    all_video_ids = set()
    dataset_stats = {}

    for ds_name in DATASETS:
        video_ids, total_samples = get_video_ids_from_dataset(ds_name)
        dataset_stats[ds_name] = {
            "samples": total_samples,
            "unique_videos": len(video_ids),
        }
        all_video_ids.update(video_ids)

    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    print("\n[Dataset별 통계]")
    for ds_name, stats in dataset_stats.items():
        short_name = ds_name.split("/")[-1]
        print(f"  {short_name}:")
        print(f"    - 샘플 수: {stats['samples']:,}")
        print(f"    - 고유 영상 수: {stats['unique_videos']:,}")

    print(f"\n[전체 통계]")
    print(f"  4개 데이터셋 통합 고유 영상 수: {len(all_video_ids):,}개")

    print(f"\n[예상 용량]")
    for estimate_name, mb_per_video in SIZE_ESTIMATES.items():
        total_mb = len(all_video_ids) * mb_per_video
        total_gb = total_mb / 1024
        total_tb = total_gb / 1024

        if total_tb >= 1:
            print(f"  {estimate_name} ({mb_per_video}MB/영상): {total_tb:.1f} TB")
        else:
            print(f"  {estimate_name} ({mb_per_video}MB/영상): {total_gb:.0f} GB")

    # Save video IDs to file
    output_file = "all_required_video_ids.txt"
    with open(output_file, "w") as f:
        for vid_id in sorted(all_video_ids):
            f.write(vid_id + "\n")
    print(f"\n고유 영상 ID 목록 저장됨: {output_file}")


if __name__ == "__main__":
    main()
