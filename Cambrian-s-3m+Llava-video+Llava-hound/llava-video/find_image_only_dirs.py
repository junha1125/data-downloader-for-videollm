#!/usr/bin/env python3
"""
Find directories that contain only images (no video files) in a dataset.
For each top-level dataset directory, create a txt file listing all image-only subdirectories.
"""

import os
from pathlib import Path
from collections import defaultdict

# Video file extensions to check
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}

# Image file extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}


def has_video_files(directory):
    """Check if directory or its subdirectories contain any video files."""
    for root, dirs, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in VIDEO_EXTENSIONS:
                return True
    return False


def get_video_formats(directory):
    """Get set of video formats found in directory and subdirectories."""
    formats = set()
    for root, dirs, files in os.walk(directory):
        for file in files:
            ext = Path(file).suffix.lower()
            if ext in VIDEO_EXTENSIONS:
                formats.add(ext)
    return formats


def has_image_files(directory):
    """Check if directory contains any image files."""
    for root, dirs, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in IMAGE_EXTENSIONS:
                return True
    return False


def find_image_only_directories(root_path):
    """
    Find all directories that contain only images (no videos).
    Returns a dictionary: {dataset_name: [list of image-only dirs]}
    """
    root_path = Path(root_path)
    results = defaultdict(list)
    
    # Get all top-level dataset directories
    dataset_dirs = [d for d in root_path.iterdir() if d.is_dir()]
    
    for dataset_dir in dataset_dirs:
        dataset_name = dataset_dir.name
        print(f"\n검사 중: {dataset_name}")
        
        # Check if the dataset directory itself has videos
        video_formats = get_video_formats(dataset_dir)
        
        if video_formats:
            # Format the extensions nicely (remove dots)
            format_str = ", ".join(sorted([fmt.lstrip('.') for fmt in video_formats]))
            print(f"  ├─ 영상 파일 발견됨 ({format_str})")
            
            # If it has videos, find subdirectories that don't have videos
            for root, dirs, files in os.walk(dataset_dir):
                root_path_obj = Path(root)
                
                # Skip if current directory has video files
                current_has_video = any(
                    Path(f).suffix.lower() in VIDEO_EXTENSIONS 
                    for f in files
                )
                
                if not current_has_video:
                    # Check if this directory or subdirectories have videos
                    if not has_video_files(root_path_obj) and has_image_files(root_path_obj):
                        # Get relative path from dataset root
                        rel_path = root_path_obj.relative_to(dataset_dir.parent)
                        results[dataset_name].append(str(rel_path))
                        print(f"  ├─ 이미지만 발견: {rel_path}")
        else:
            # No videos in entire dataset
            if has_image_files(dataset_dir):
                # Dataset has only images
                results[dataset_name].append(f"{dataset_name} (전체 디렉토리)")
                print(f"  └─ ✓ 영상 없음 - 이미지만 존재")
            else:
                results[dataset_name].append(f"{dataset_name} (이미지도 영상도 없음)")
                print(f"  └─ ⚠ 영상 없음 - 이미지도 없음")
    
    return results


class Logger:
    """Simple logger that prints to console and writes to file."""
    def __init__(self, filename):
        self.terminal = __import__('sys').stdout
        self.log = open(filename, 'w', encoding='utf-8')
    
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    
    def flush(self):
        self.terminal.flush()
        self.log.flush()
    
    def close(self):
        self.log.close()


def main():
    import sys
    
    # 데이터셋 루트 경로 설정
    dataset_root = "/mnt/ddn/datasets/cambrian_s_3m"
    output_file = "/mnt/ddn/datasets/cambrian_s_3m/image_only_results.txt"
    
    # Create logger that prints and saves to file
    logger = Logger(output_file)
    sys.stdout = logger
    
    try:
        # 경로가 존재하는지 확인
        if not os.path.exists(dataset_root):
            print(f"❌ 경로가 존재하지 않습니다: {dataset_root}")
            print("경로를 확인하고 다시 시도해주세요.")
            return
        
        print(f"데이터셋 루트: {dataset_root}")
        print(f"결과 저장 위치: {output_file}")
        print("=" * 80)
        
        # 이미지 전용 디렉토리 찾기
        results = find_image_only_directories(dataset_root)
        
        print("\n" + "=" * 80)
        print("완료!")
        print(f"총 {len(results)}개의 데이터셋 검사됨")
        
    finally:
        # Restore stdout and close log file
        sys.stdout = logger.terminal
        logger.close()
        print(f"\n결과가 저장되었습니다: {output_file}")


if __name__ == "__main__":
    main()