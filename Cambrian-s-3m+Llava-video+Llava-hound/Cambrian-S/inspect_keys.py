# import json
# import sys
# from collections import Counter

# """
# python inspect_keys.py cambrian_s_3m_filtered.jsonl
# """

# def main():
#     path = sys.argv[1] if len(sys.argv) > 1 else "cambrian_s_3m_filtered.jsonl"

#     key_counter = Counter()
#     has_video = 0
#     no_video = 0
#     total = 0

#     with open(path, "r") as f:
#         for line in f:
#             line = line.strip()
#             if not line:
#                 continue
#             data = json.loads(line)
#             total += 1

#             for k in data.keys():
#                 key_counter[k] += 1

#             if "video" in data:
#                 has_video += 1
#             else:
#                 no_video += 1

#     print(f"Total entries: {total:,}")
#     print(f"\n{'='*40}")
#     print(f"{'Key':<25} {'Count':>10} {'%':>8}")
#     print(f"{'='*40}")
#     for key, count in key_counter.most_common():
#         print(f"{key:<25} {count:>10,} {count/total*100:>7.2f}%")

#     print(f"\n{'='*40}")
#     print(f"Has 'video' key:    {has_video:>10,}")
#     print(f"No 'video' key:     {no_video:>10,}")
#     print(f"{'='*40}")


# if __name__ == "__main__":
#     main()

import json
import sys

"""
python inspect_keys.py cambrian_s_3m_filtered.jsonl
"""

CORE_KEYS = {"id", "conversations", "video", "data_source", "task", "instruction", "type"}

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "cambrian_s_3m_filtered.jsonl"
    output = path.replace(".jsonl", "_extra_keys.jsonl")

    total = 0
    extra_count = 0

    with open(path, "r") as fin, open(output, "w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            total += 1
            data = json.loads(line)

            extra_keys = set(data.keys()) - CORE_KEYS
            if extra_keys:
                fout.write(json.dumps(data, ensure_ascii=False) + "\n")
                extra_count += 1

    print(f"Total: {total:,}")
    print(f"Has extra keys: {extra_count:,} ({extra_count/total*100:.2f}%)")
    print(f"Saved to {output}")


if __name__ == "__main__":
    main()