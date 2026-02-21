import json
import sys
import random
import os
from collections import defaultdict

def format_table(title, counts, unit_seconds, format_label_fn):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")
    print(f"  {'구간':<25} {'데이터 수':>10} {'비율':>10}")
    print(f"  {'-'*43}")
    total = sum(counts.values())
    for key in sorted(counts.keys()):
        label = format_label_fn(key, unit_seconds)
        count = counts[key]
        ratio = count / total * 100 if total > 0 else 0
        print(f"  {label:<25} {count:>10,} {ratio:>9.2f}%")
    print(f"  {'-'*43}")
    print(f"  {'합계':<25} {total:>10,} {'100.00%':>10}")
    print(f"{'='*55}")

def seconds_to_label_30s(bucket, unit):
    start = bucket * unit
    end = (bucket + 1) * unit
    return f"{start}s ~ {end}s"

def seconds_to_label_5min(bucket, unit):
    start_sec = bucket * unit
    end_sec = (bucket + 1) * unit
    start_min = start_sec // 60
    end_min = end_sec // 60
    return f"{start_min}min ~ {end_min}min"

def parse_args():
    args = sys.argv[1:]
    if len(args) < 4:
        print("Usage: python print_video_duration_hist.py <jsonl_file> <pivot_min> <short_%> <long_%>")
        print("  예시: python print_video_duration_hist.py data.jsonl 2 10 100")
        print("  pivot_min  : 분 단위 기준점 (정수)")
        print("  short_%    : pivot 미만 데이터 추출 비율 (0~100)")
        print("  long_%     : pivot 이상 데이터 추출 비율 (0~100)")
        sys.exit(1)

    filepath = args[0]
    pivot_min = int(args[1])
    short_pct = float(args[2])
    long_pct  = float(args[3])

    if not (0 <= short_pct <= 100) or not (0 <= long_pct <= 100):
        print("오류: 퍼센트 값은 0~100 사이여야 합니다.")
        sys.exit(1)

    return filepath, pivot_min, short_pct, long_pct

def main():
    filepath, pivot_min, short_pct, long_pct = parse_args()
    pivot_sec = pivot_min * 60

    print(f"\n파일 로딩 중: {filepath}")
    print(f"설정 → pivot: {pivot_min}분({pivot_sec}초) | short: {short_pct}% | long: {long_pct}%")

    short_data = []  # pivot 미만
    long_data  = []  # pivot 이상
    counts_30s  = defaultdict(int)
    counts_5min = defaultdict(int)
    total_lines = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if (i + 1) % 500_000 == 0:
                print(f"  {i+1:,}개 처리 중...")
            line = line.strip()
            if not line:
                continue
            total_lines += 1
            data = json.loads(line)
            duration = data.get("video_duration", None)
            if duration is None:
                continue

            # 히스토그램 버킷
            counts_30s[int(duration // 30)] += 1
            counts_5min[int(duration // 300)] += 1

            if duration < pivot_sec:
                short_data.append(line)
            else:
                long_data.append(line)

    print(f"\n총 {total_lines:,}개 데이터 로딩 완료!")
    all_durations_count = len(short_data) + len(long_data)
    print(f"  {pivot_min}분 미만: {len(short_data):,}개")
    print(f"  {pivot_min}분 이상: {len(long_data):,}개")

    # 분포 테이블 출력
    format_table("30초 단위 분포", counts_30s, 30, seconds_to_label_30s)
    format_table("5분 단위 분포", counts_5min, 300, seconds_to_label_5min)

    # --- 샘플링 및 저장 ---
    base = os.path.splitext(filepath)[0]
    short_pct_int = int(short_pct)
    long_pct_int  = int(long_pct)

    out_short = f"{base}_under_{pivot_min}m_{short_pct_int}p.jsonl"
    out_long  = f"{base}_over_{pivot_min}m_{long_pct_int}p.jsonl"

    print(f"\n{'='*55}")
    print("  샘플링 및 저장")
    print(f"{'='*55}")

    # short 샘플링
    random.shuffle(short_data)
    n_short = max(1, round(len(short_data) * short_pct / 100))
    sampled_short = short_data[:n_short]
    print(f"\n  [under {pivot_min}min] {len(short_data):,}개 중 {short_pct}% → {n_short:,}개 추출")
    print(f"  저장 중: {out_short}")
    with open(out_short, "w", encoding="utf-8") as f:
        f.write("\n".join(sampled_short) + "\n")
    print(f"  ✓ 저장 완료: {out_short}")

    # long 샘플링
    random.shuffle(long_data)
    n_long = max(1, round(len(long_data) * long_pct / 100)) if long_data else 0
    sampled_long = long_data[:n_long]
    print(f"\n  [over  {pivot_min}min] {len(long_data):,}개 중 {long_pct}% → {n_long:,}개 추출")
    print(f"  저장 중: {out_long}")
    with open(out_long, "w", encoding="utf-8") as f:
        if sampled_long:
            f.write("\n".join(sampled_long) + "\n")
    print(f"  ✓ 저장 완료: {out_long}")

    total_out = n_short + n_long
    print(f"\n  최종 출력 합계: {total_out:,}개 ({total_out/all_durations_count*100:.2f}% of original)")
    print(f"{'='*55}\n")

if __name__ == "__main__":
    main()