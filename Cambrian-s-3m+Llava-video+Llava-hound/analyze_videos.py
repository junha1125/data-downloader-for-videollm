#!/usr/bin/env python3
"""
Analyze video files in datasets to get resolution and duration statistics.
For each dataset, calculate min/max/avg resolution and duration.
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import subprocess
import json


# Video file extensions to check
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}


class Logger:
    """Simple logger that prints to console and writes to file."""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'w', encoding='utf-8')
    
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    
    def flush(self):
        self.terminal.flush()
        self.log.flush()
    
    def close(self):
        self.log.close()


def get_video_info(video_path):
    """
    Get video resolution and duration using ffprobe.
    Returns: (width, height, duration_seconds) or None if failed
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration',
            '-show_entries', 'format=duration',
            '-of', 'json',
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return None
        
        data = json.loads(result.stdout)
        
        # Get resolution from stream
        if 'streams' in data and len(data['streams']) > 0:
            stream = data['streams'][0]
            width = stream.get('width')
            height = stream.get('height')
            duration = stream.get('duration')
            
            # If duration not in stream, try format
            if duration is None and 'format' in data:
                duration = data['format'].get('duration')
            
            if width and height:
                duration = float(duration) if duration else 0.0
                return (int(width), int(height), duration)
        
        return None
        
    except Exception as e:
        print(f"    ⚠ 오류 ({video_path.name}): {e}")
        return None


def find_video_files(directory, exclude_image_dirs=True):
    """
    Find all video files in directory.
    If exclude_image_dirs is True, skip directories named 'image' or 'images'.
    """
    video_files = []
    directory = Path(directory)
    
    for root, dirs, files in os.walk(directory):
        # Skip 'image' or 'images' directories
        if exclude_image_dirs:
            dirs[:] = [d for d in dirs if d.lower() not in ['image', 'images']]
        
        for file in files:
            if Path(file).suffix.lower() in VIDEO_EXTENSIONS:
                video_files.append(Path(root) / file)
    
    return video_files


def analyze_dataset(dataset_path, dataset_name):
    """Analyze all videos in a dataset and return statistics."""
    print(f"\n{'='*80}")
    print(f"분석 중: {dataset_name}")
    print(f"{'='*80}")
    
    video_files = find_video_files(dataset_path, exclude_image_dirs=True)
    
    if not video_files:
        print("  ⚠ 비디오 파일을 찾을 수 없습니다.")
        return None
    
    print(f"  총 {len(video_files)}개의 비디오 파일 발견")
    
    # Collect video info
    widths = []
    heights = []
    durations = []
    
    failed_count = 0
    for i, video_file in enumerate(video_files, 1):
        if i % 100 == 0:
            print(f"  진행: {i}/{len(video_files)} ({i*100//len(video_files)}%)")
        
        info = get_video_info(video_file)
        if info:
            width, height, duration = info
            widths.append(width)
            heights.append(height)
            durations.append(duration)
        else:
            failed_count += 1
    
    if not widths:
        print("  ⚠ 비디오 정보를 추출할 수 없습니다.")
        return None
    
    # Calculate statistics
    stats = {
        'dataset': dataset_name,
        'total_videos': len(video_files),
        'analyzed_videos': len(widths),
        'failed_videos': failed_count,
        'resolution': {
            'width': {
                'min': min(widths),
                'max': max(widths),
                'avg': sum(widths) / len(widths)
            },
            'height': {
                'min': min(heights),
                'max': max(heights),
                'avg': sum(heights) / len(heights)
            }
        },
        'duration': {
            'min': min(durations),
            'max': max(durations),
            'avg': sum(durations) / len(durations)
        }
    }
    
    return stats


def print_statistics(stats):
    """Print statistics in a readable format."""
    if not stats:
        return
    
    print(f"\n결과:")
    print(f"  분석된 비디오: {stats['analyzed_videos']}/{stats['total_videos']}")
    if stats['failed_videos'] > 0:
        print(f"  실패: {stats['failed_videos']}")
    
    print(f"\n  해상도 (너비):")
    print(f"    최소: {stats['resolution']['width']['min']} px")
    print(f"    최대: {stats['resolution']['width']['max']} px")
    print(f"    평균: {stats['resolution']['width']['avg']:.1f} px")
    
    print(f"\n  해상도 (높이):")
    print(f"    최소: {stats['resolution']['height']['min']} px")
    print(f"    최대: {stats['resolution']['height']['max']} px")
    print(f"    평균: {stats['resolution']['height']['avg']:.1f} px")
    
    print(f"\n  영상 길이:")
    print(f"    최소: {stats['duration']['min']:.2f} 초")
    print(f"    최대: {stats['duration']['max']:.2f} 초")
    print(f"    평균: {stats['duration']['avg']:.2f} 초")


def main():
    # Dataset root path
    dataset_root = "/mnt/ddn/datasets/cambrian_s_3m"
    output_file = os.path.join(dataset_root, "video_analysis_results.txt")
    
    # Datasets to analyze
    dir_list = [
        'star', 'EgoTask', 'vript_short', 'vidln', 'favd', 'k710', 'timeit', 
        'EGTEA', 'activitynet', 'sharegpt4o', 'EgoProceL', 'moviechat', 
        'textvr', 'ssv2', 'clevrer', 'nturgbd', 'nextqa', 'Ego4d', 
        'HoloAssist', 'ADL', 'IndustReal', 'ChardesEgo', 'Ego4d_clip', 
        'guiworld', 'lsmdc', 'vript_long', 'webvid', 'EpicKitchens', 
        'youcook2', 'k400_targz'
    ]
    
    # Create logger
    logger = Logger(output_file)
    sys.stdout = logger
    
    try:
        print(f"비디오 분석 시작")
        print(f"데이터셋 루트: {dataset_root}")
        print(f"분석할 데이터셋: {len(dir_list)}개")
        
        all_stats = []
        
        for dataset_name in dir_list:
            dataset_path = Path(dataset_root) / dataset_name
            
            if not dataset_path.exists():
                print(f"\n{'='*80}")
                print(f"⚠ 경로가 존재하지 않음: {dataset_name}")
                print(f"{'='*80}")
                continue
            
            stats = analyze_dataset(dataset_path, dataset_name)
            if stats:
                print_statistics(stats)
                all_stats.append(stats)
        
        # Print summary
        print(f"\n\n{'='*80}")
        print(f"전체 요약")
        print(f"{'='*80}")
        print(f"총 {len(all_stats)}개 데이터셋 분석 완료\n")
        
        for stats in all_stats:
            print(f"{stats['dataset']:20s} | "
                  f"Videos: {stats['analyzed_videos']:6d} | "
                  f"Res: {stats['resolution']['width']['avg']:.0f}x{stats['resolution']['height']['avg']:.0f} | "
                  f"Dur: {stats['duration']['avg']:.1f}s")
        
    finally:
        sys.stdout = logger.terminal
        logger.close()
        print(f"\n결과가 저장되었습니다: {output_file}")


if __name__ == "__main__":
    main()