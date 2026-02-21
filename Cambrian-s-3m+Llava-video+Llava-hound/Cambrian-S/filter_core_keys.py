import json
import sys
from tqdm import tqdm

"""
python filter_core_keys.py cambrian_s_3m_filtered.jsonl
"""

CORE_KEYS = {"id", "conversations", "video", "data_source", "task", "instruction", "type", "video_duration"}

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "cambrian_s_3m_filtered.jsonl"
    output_extra = path.replace(".jsonl", "_extra_keys.jsonl")
    output_core = path.replace(".jsonl", "_core_keys.jsonl")

    # 전체 라인 수 미리 파악 (tqdm 진행률 표시용)
    print(f"📂 Input : {path}")
    print(f"Counting lines...", end="\r")
    with open(path, "r") as f:
        total_lines = sum(1 for line in f if line.strip())
    print(f"Total lines: {total_lines:,}          ")

    total = 0
    extra_count = 0
    core_count = 0
    extra_key_counter = {}  # 어떤 extra key가 얼마나 등장하는지 추적

    with open(path, "r") as fin, \
         open(output_extra, "w") as fout_extra, \
         open(output_core, "w") as fout_core:

        pbar = tqdm(fin, total=total_lines, desc="Filtering", unit="lines", dynamic_ncols=True)
        for line in pbar:
            line = line.strip()
            if not line:
                continue
            total += 1
            data = json.loads(line)

            extra_keys = set(data.keys()) - CORE_KEYS
            if extra_keys:
                fout_extra.write(json.dumps(data, ensure_ascii=False) + "\n")
                extra_count += 1
                for k in extra_keys:
                    extra_key_counter[k] = extra_key_counter.get(k, 0) + 1
            else:
                fout_core.write(json.dumps(data, ensure_ascii=False) + "\n")
                core_count += 1

            # tqdm postfix로 실시간 현황 표시
            pbar.set_postfix({
                "core": f"{core_count:,}",
                "extra": f"{extra_count:,}",
                "extra%": f"{extra_count/total*100:.1f}%",
            })

    print("\n" + "="*50)
    print(f"{'Total':<20}: {total:,}")
    print(f"{'Core keys only':<20}: {core_count:,}  ({core_count/total*100:.2f}%)")
    print(f"{'Has extra keys':<20}: {extra_count:,}  ({extra_count/total*100:.2f}%)")
    print("="*50)

    if extra_key_counter:
        print("\n📌 Extra key 분포 (등장 횟수 순):")
        for k, v in sorted(extra_key_counter.items(), key=lambda x: -x[1]):
            print(f"  {k:<30}: {v:,}  ({v/total*100:.2f}%)")

    print(f"\n💾 Saved extra → {output_extra}")
    print(f"💾 Saved core  → {output_core}")


if __name__ == "__main__":
    main()