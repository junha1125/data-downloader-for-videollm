#!/usr/bin/env python3
"""
Molmo2 YouTube 비디오 다운로드 스크립트

특징:
- YouTube에서 직접 다운로드 (무료)
- 최대 480p 해상도
- mp4 포맷 (작은 파일 크기)
- 멀티스레드 병렬 다운로드
- 느린 다운로드 자동 스킵 (타임아웃)
- 진행 상황 실시간 추적
- 중단 후 재개 지원

사용법:
    # 테스트 (5개만)
    python download_youtube.py --test

    # 전체 다운로드
    python download_youtube.py

    # 워커 수 지정
    python download_youtube.py --workers 8

    # 재개 (이미 받은 파일 스킵)
    python download_youtube.py --resume
"""

import json
import os
import subprocess
import argparse
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from collections import defaultdict
import signal
import sys

# ffmpeg 경로 설정
def get_ffmpeg_path():
    """ffmpeg 경로 찾기 및 symlink 생성"""
    # 시스템 ffmpeg 확인
    result = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()

    # imageio-ffmpeg 확인
    try:
        import imageio_ffmpeg
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_dir = os.path.dirname(ffmpeg_bin)
        ffmpeg_link = os.path.join(ffmpeg_dir, "ffmpeg")

        # symlink가 없으면 생성
        if not os.path.exists(ffmpeg_link):
            try:
                os.symlink(ffmpeg_bin, ffmpeg_link)
                print(f"ffmpeg symlink 생성: {ffmpeg_link}")
            except Exception as e:
                print(f"ffmpeg symlink 생성 실패: {e}")

        return ffmpeg_link if os.path.exists(ffmpeg_link) else ffmpeg_bin
    except ImportError:
        pass

    return None

FFMPEG_PATH = get_ffmpeg_path()


class DownloadStats:
    """다운로드 통계 추적"""
    def __init__(self):
        self.lock = threading.Lock()
        self.success = 0
        self.failed = 0
        self.skipped = 0
        self.timeout = 0
        self.unavailable = 0
        self.total_bytes = 0
        self.start_time = time.time()
        self.errors = []

    def add_success(self, size_bytes=0):
        with self.lock:
            self.success += 1
            self.total_bytes += size_bytes

    def add_failed(self, video_id, error):
        with self.lock:
            self.failed += 1
            self.errors.append((video_id, error))

    def add_skipped(self):
        with self.lock:
            self.skipped += 1

    def add_timeout(self, video_id):
        with self.lock:
            self.timeout += 1
            self.errors.append((video_id, "Timeout - too slow"))

    def add_unavailable(self, video_id):
        with self.lock:
            self.unavailable += 1
            self.errors.append((video_id, "Video unavailable"))

    def get_summary(self):
        elapsed = time.time() - self.start_time
        speed = self.total_bytes / elapsed / 1024 / 1024 if elapsed > 0 else 0  # MB/s
        return {
            "success": self.success,
            "failed": self.failed,
            "skipped": self.skipped,
            "timeout": self.timeout,
            "unavailable": self.unavailable,
            "total_bytes": self.total_bytes,
            "elapsed_seconds": elapsed,
            "speed_mbps": speed,
        }


def load_required_video_ids(filepath="all_required_video_ids.txt"):
    """필요한 비디오 ID 목록 로드"""
    with open(filepath, "r") as f:
        return [line.strip() for line in f if line.strip()]


def load_url_mapping(filepath="youtube_id_to_urls_mapping.json"):
    """비디오 ID -> URL 매핑 로드"""
    with open(filepath, "r") as f:
        return json.load(f)


def get_output_path(video_id, output_dir):
    """출력 파일 경로 생성"""
    return os.path.join(output_dir, f"{video_id}.mp4")


def check_existing_file(video_id, output_dir):
    """이미 다운로드된 파일 확인"""
    output_path = get_output_path(video_id, output_dir)
    if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:  # 최소 10KB
        return True, output_path
    return False, output_path


def download_video(video_id, youtube_url, output_dir, timeout=120, speed_limit_kb=50):
    """
    yt-dlp를 사용하여 비디오 다운로드

    Args:
        video_id: 비디오 ID
        youtube_url: YouTube URL
        output_dir: 출력 디렉토리
        timeout: 최대 다운로드 시간 (초)
        speed_limit_kb: 이 속도(KB/s) 이하로 떨어지면 타임아웃으로 간주

    Returns:
        dict: 결과 정보
    """
    output_path = get_output_path(video_id, output_dir)
    temp_path = os.path.join(output_dir, f"{video_id}.%(ext)s")

    # yt-dlp 옵션
    cmd = [
        "yt-dlp",
        # 포맷: 480p 이하, mp4 선호, 작은 파일 우선
        "-f", "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/bestvideo[height<=480]+bestaudio/best[height<=480]/best",
        # 출력 형식
        "--merge-output-format", "mp4",
        # 출력 경로
        "-o", temp_path,
        # 조용한 모드 (에러만 출력)
        "--no-warnings",
        "-q",
        # 진행률 표시 안함
        "--no-progress",
        # 재시도 설정
        "--retries", "2",
        "--fragment-retries", "2",
        # 속도 제한 감지를 위한 버퍼 설정
        "--buffer-size", "16K",
        # 이미 있으면 스킵
        "--no-overwrites",
        # 메타데이터 스킵 (속도 향상)
        "--no-write-info-json",
        "--no-write-thumbnail",
        "--no-write-description",
        # URL
        youtube_url,
    ]

    # ffmpeg 경로 추가
    if FFMPEG_PATH:
        cmd.insert(1, "--ffmpeg-location")
        cmd.insert(2, os.path.dirname(FFMPEG_PATH))

    try:
        # 타임아웃과 함께 실행
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # 다운로드된 파일 확인 (확장자가 다를 수 있음)
        actual_path = None
        for ext in [".mp4", ".mkv", ".webm"]:
            check_path = os.path.join(output_dir, f"{video_id}{ext}")
            if os.path.exists(check_path) and os.path.getsize(check_path) > 10000:
                actual_path = check_path
                break

        if actual_path:
            file_size = os.path.getsize(actual_path)
            # mp4가 아니면 이름 변경
            if actual_path != output_path and os.path.exists(actual_path):
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(actual_path, output_path)
            return {
                "status": "success",
                "video_id": video_id,
                "path": output_path,
                "size": file_size,
            }
        else:
            # 파일이 없으면 에러 확인
            stderr = result.stderr.lower() if result.stderr else ""
            if "unavailable" in stderr or "private" in stderr or "removed" in stderr or "not available" in stderr:
                return {"status": "unavailable", "video_id": video_id, "error": result.stderr}
            return {"status": "failed", "video_id": video_id, "error": result.stderr or "Unknown error"}

    except subprocess.TimeoutExpired:
        # 타임아웃 - 부분 다운로드 파일 정리
        for ext in [".mp4", ".mkv", ".webm", ".part", ".ytdl"]:
            temp_file = os.path.join(output_dir, f"{video_id}{ext}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
        return {"status": "timeout", "video_id": video_id}

    except Exception as e:
        return {"status": "failed", "video_id": video_id, "error": str(e)}


def print_progress(stats, total, current):
    """진행 상황 출력"""
    summary = stats.get_summary()
    elapsed = timedelta(seconds=int(summary["elapsed_seconds"]))

    # 예상 남은 시간 계산
    completed = summary["success"] + summary["failed"] + summary["timeout"] + summary["unavailable"]
    if completed > 0:
        rate = completed / summary["elapsed_seconds"]
        remaining = (total - current) / rate if rate > 0 else 0
        eta = timedelta(seconds=int(remaining))
    else:
        eta = "계산중..."

    total_mb = summary["total_bytes"] / 1024 / 1024

    print(f"\r[{current}/{total}] "
          f"성공:{summary['success']} "
          f"실패:{summary['failed']} "
          f"타임아웃:{summary['timeout']} "
          f"삭제됨:{summary['unavailable']} "
          f"스킵:{summary['skipped']} | "
          f"{total_mb:.1f}MB | "
          f"{summary['speed_mbps']:.2f}MB/s | "
          f"경과:{elapsed} | ETA:{eta}    ", end="", flush=True)


def save_progress(stats, output_dir):
    """진행 상황 저장"""
    summary = stats.get_summary()
    progress_file = os.path.join(output_dir, "download_progress.json")

    with open(progress_file, "w") as f:
        json.dump({
            "last_update": datetime.now().isoformat(),
            "stats": summary,
            "errors": stats.errors[-100:],  # 최근 100개 에러만 저장
        }, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Molmo2 YouTube 비디오 다운로드")
    parser.add_argument("--test", action="store_true", help="테스트 모드 (5개만)")
    parser.add_argument("--output", type=str, default="molmo2-videos", help="출력 디렉토리")
    parser.add_argument("--workers", type=int, default=4, help="병렬 다운로드 수 (기본: 4)")
    parser.add_argument("--timeout", type=int, default=120, help="영상당 최대 다운로드 시간(초) (기본: 120)")
    parser.add_argument("--resume", action="store_true", help="이전 다운로드 재개 (기존 파일 스킵)")
    parser.add_argument("--start", type=int, default=0, help="시작 인덱스")
    parser.add_argument("--limit", type=int, default=0, help="최대 다운로드 수 (0=무제한)")
    args = parser.parse_args()

    # 항상 resume 모드로 동작 (기존 파일 스킵)
    args.resume = True

    print("="*60)
    print("Molmo2 YouTube 비디오 다운로드")
    print("="*60)

    # 파일 로드
    print("\n필요한 비디오 ID 로드 중...")
    video_ids = load_required_video_ids()
    print(f"총 {len(video_ids):,}개 비디오 필요")

    print("URL 매핑 로드 중...")
    url_mapping = load_url_mapping()

    # 다운로드 목록 생성
    videos_to_download = []
    missing_mapping = 0

    for vid_id in video_ids:
        if vid_id in url_mapping:
            youtube_url = url_mapping[vid_id].get("youtube_url")
            if youtube_url:
                videos_to_download.append((vid_id, youtube_url))
            else:
                missing_mapping += 1
        else:
            missing_mapping += 1

    if missing_mapping > 0:
        print(f"경고: {missing_mapping}개 비디오의 YouTube URL이 없음")

    # 범위 적용
    if args.start > 0:
        videos_to_download = videos_to_download[args.start:]
    if args.limit > 0:
        videos_to_download = videos_to_download[:args.limit]
    if args.test:
        videos_to_download = videos_to_download[:5]
        print(f"\n테스트 모드: 5개만 다운로드")

    print(f"다운로드 대상: {len(videos_to_download):,}개")

    # 출력 디렉토리 생성
    os.makedirs(args.output, exist_ok=True)

    # 이미 다운로드된 파일 확인
    if args.resume:
        filtered_videos = []
        skipped_count = 0
        for vid_id, url in videos_to_download:
            exists, _ = check_existing_file(vid_id, args.output)
            if exists:
                skipped_count += 1
            else:
                filtered_videos.append((vid_id, url))

        if skipped_count > 0:
            print(f"이미 다운로드됨 (스킵): {skipped_count:,}개")
        videos_to_download = filtered_videos

    if not videos_to_download:
        print("\n다운로드할 새 비디오가 없습니다!")
        return

    print(f"실제 다운로드할 비디오: {len(videos_to_download):,}개")
    print(f"\n설정:")
    print(f"  - 워커 수: {args.workers}")
    print(f"  - 타임아웃: {args.timeout}초")
    print(f"  - 출력 디렉토리: {args.output}")
    print(f"  - 최대 해상도: 480p")
    print(f"  - 포맷: mp4")

    # 통계 초기화
    stats = DownloadStats()
    total = len(videos_to_download)

    # Ctrl+C 핸들러
    stop_flag = threading.Event()

    def signal_handler(sig, frame):
        print("\n\n중단 요청됨... 현재 다운로드 완료 후 종료합니다.")
        stop_flag.set()

    signal.signal(signal.SIGINT, signal_handler)

    print(f"\n다운로드 시작...\n")

    # 병렬 다운로드 실행
    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}

        for vid_id, url in videos_to_download:
            if stop_flag.is_set():
                break
            future = executor.submit(
                download_video,
                vid_id,
                url,
                args.output,
                args.timeout
            )
            futures[future] = vid_id

        for future in as_completed(futures):
            if stop_flag.is_set():
                break

            result = future.result()
            completed += 1

            if result["status"] == "success":
                stats.add_success(result.get("size", 0))
            elif result["status"] == "timeout":
                stats.add_timeout(result["video_id"])
            elif result["status"] == "unavailable":
                stats.add_unavailable(result["video_id"])
            else:
                stats.add_failed(result["video_id"], result.get("error", "Unknown"))

            # 진행 상황 출력 (10개마다)
            if completed % 10 == 0 or completed == total:
                print_progress(stats, total, completed)

            # 진행 상황 저장 (100개마다)
            if completed % 100 == 0:
                save_progress(stats, args.output)

    # 최종 결과
    print("\n\n" + "="*60)
    print("다운로드 완료!")
    print("="*60)

    summary = stats.get_summary()
    total_mb = summary["total_bytes"] / 1024 / 1024
    total_gb = total_mb / 1024
    elapsed = timedelta(seconds=int(summary["elapsed_seconds"]))

    print(f"\n[결과]")
    print(f"  성공: {summary['success']:,}개")
    print(f"  실패: {summary['failed']:,}개")
    print(f"  타임아웃: {summary['timeout']:,}개")
    print(f"  영상 삭제/비공개: {summary['unavailable']:,}개")
    print(f"  스킵 (기존): {summary['skipped']:,}개")

    print(f"\n[통계]")
    print(f"  총 다운로드: {total_gb:.2f} GB ({total_mb:.0f} MB)")
    print(f"  평균 속도: {summary['speed_mbps']:.2f} MB/s")
    print(f"  소요 시간: {elapsed}")

    if summary['success'] > 0:
        avg_size = total_mb / summary['success']
        print(f"  평균 파일 크기: {avg_size:.1f} MB")

    # 에러 목록 저장
    if stats.errors:
        error_file = os.path.join(args.output, "download_errors.txt")
        with open(error_file, "w") as f:
            for vid_id, error in stats.errors:
                f.write(f"{vid_id}\t{error}\n")
        print(f"\n에러 목록 저장됨: {error_file}")

    # 최종 진행 상황 저장
    save_progress(stats, args.output)
    print(f"진행 상황 저장됨: {os.path.join(args.output, 'download_progress.json')}")


if __name__ == "__main__":
    main()
