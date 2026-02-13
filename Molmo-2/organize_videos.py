#!/usr/bin/env python3
"""
molmo2-videos 폴더의 영상을 200개씩 서브폴더로 분배하고,
영상이름 -> 폴더 매핑 JSON을 생성하는 스크립트.

사용법:
    python organize_videos.py
    python organize_videos.py --src molmo2-videos --per-folder 200
"""

import os
import json
import argparse


def main():
    parser = argparse.ArgumentParser(description="비디오 파일을 서브폴더로 분배")
    parser.add_argument("--src", default="molmo2-videos", help="원본 비디오 폴더 (기본: molmo2-videos)")
    parser.add_argument("--per-folder", type=int, default=200, help="폴더당 파일 수 (기본: 200)")
    args = parser.parse_args()

    src_dir = args.src
    per_folder = args.per_folder

    if not os.path.isdir(src_dir):
        print(f"오류: '{src_dir}' 폴더가 존재하지 않습니다.")
        return

    # 비디오 파일 목록 수집 (파일만, 디렉토리 제외)
    files = sorted(
        f for f in os.listdir(src_dir)
        if os.path.isfile(os.path.join(src_dir, f))
    )

    if not files:
        print("이동할 파일이 없습니다.")
        return

    print(f"총 파일 수: {len(files):,}개")
    print(f"폴더당 파일 수: {per_folder}개")
    print(f"생성될 폴더 수: {(len(files) + per_folder - 1) // per_folder}개")

    mapping = {}  # filename -> folder_name

    for i, filename in enumerate(files):
        folder_idx = i // per_folder + 1
        folder_name = f"molmo2-videos-{folder_idx:03d}"
        folder_path = os.path.join(os.path.dirname(src_dir.rstrip("/")), folder_name)

        if not os.path.isdir(folder_path):
            os.makedirs(folder_path)

        old_path = os.path.join(src_dir, filename)
        new_path = os.path.join(folder_path, filename)
        os.rename(old_path, new_path)

        mapping[filename] = folder_name

        if (i + 1) % 1000 == 0:
            print(f"  {i + 1:,}/{len(files):,} 이동 완료...")

    # 매핑 JSON 저장 (원본 폴더와 같은 레벨에)
    mapping_path = os.path.join(os.path.dirname(src_dir.rstrip("/")), "video_folder_mapping.json")
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print(f"\n완료!")
    print(f"  이동된 파일: {len(files):,}개")
    print(f"  생성된 폴더: {(len(files) + per_folder - 1) // per_folder}개")
    print(f"  매핑 파일: {mapping_path}")


if __name__ == "__main__":
    main()
