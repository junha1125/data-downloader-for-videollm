#!/usr/bin/env python3
"""
Molmo2 YouTube 비디오 다운로드 스크립트 (폴더 분배 버전)

특징:
- 성공한 파일 200개마다 새 폴더 생성 (molmo2-videos-001, 002, ...)
- video_folder_mapping.json 자동 생성 (파일이름 -> 폴더이름)
- 임시 폴더에 다운로드 후 성공 시에만 서브폴더로 이동
- 중단 후 재개 지원 (매핑 JSON + 기존 파일 기반)
- 그 외 원본 download_youtube.py와 동일

사용법:
    python download_youtube_.py                    # 전체 다운로드
    python download_youtube_.py --test             # 테스트 (5개만)
    python download_youtube_.py --workers 8        # 워커 수 지정
    python download_youtube_.py --per-folder 300   # 폴더당 300개
"""

import json
import os
import shutil
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


# ──────────────────────────────────────────────
# ffmpeg
# ──────────────────────────────────────────────
def get_ffmpeg_path():
    result = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    try:
        import imageio_ffmpeg
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_dir = os.path.dirname(ffmpeg_bin)
        ffmpeg_link = os.path.join(ffmpeg_dir, "ffmpeg")
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


# ──────────────────────────────────────────────
# FolderManager: 서브폴더 분배 + 매핑 JSON 관리
# ──────────────────────────────────────────────
class FolderManager:
    """
    성공한 파일을 200개씩 서브폴더로 분배.
    thread-safe하게 동작.
    """

    def __init__(self, base_name="molmo2-videos", per_folder=200):
        self.base_name = base_name
        self.per_folder = per_folder
        self.lock = threading.Lock()
        self.current_index = 1
        self.current_count = 0
        self.mapping = {}           # filename -> folder_name
        self.mapping_path = "video_folder_mapping.json"
        self.temp_dir = f".{base_name}-temp"
        os.makedirs(self.temp_dir, exist_ok=True)

    # ── resume: 기존 매핑 로드 + 폴더 상태 복원 ──

    def load_existing(self):
        """기존 매핑 JSON 로드. 이미 받은 video_id set 반환."""
        if os.path.exists(self.mapping_path):
            with open(self.mapping_path, "r", encoding="utf-8") as f:
                self.mapping = json.load(f)

        # 폴더 인덱스/카운트 복원
        folder_counts = defaultdict(int)
        max_index = 0
        for folder_name in self.mapping.values():
            try:
                idx = int(folder_name.rsplit("-", 1)[-1])
                folder_counts[idx] += 1
                max_index = max(max_index, idx)
            except ValueError:
                pass

        if max_index > 0:
            last_count = folder_counts[max_index]
            if last_count >= self.per_folder:
                self.current_index = max_index + 1
                self.current_count = 0
            else:
                self.current_index = max_index
                self.current_count = last_count

        return {os.path.splitext(f)[0] for f in self.mapping}

    # ── 성공 파일을 서브폴더로 이동 ──

    def assign_file(self, video_id):
        """
        temp 폴더의 파일을 현재 서브폴더로 이동.
        폴더가 per_folder에 도달하면 다음 폴더로 넘어감.
        Returns: (folder_name, dest_path)
        """
        filename = f"{video_id}.mp4"
        src_path = os.path.join(self.temp_dir, filename)

        with self.lock:
            folder_name = f"{self.base_name}-{self.current_index:03d}"
            folder_path = folder_name
            os.makedirs(folder_path, exist_ok=True)

            dest_path = os.path.join(folder_path, filename)
            # 같은 파일시스템이면 rename (빠름), 아니면 shutil.move
            try:
                os.rename(src_path, dest_path)
            except OSError:
                shutil.move(src_path, dest_path)

            self.mapping[filename] = folder_name
            self.current_count += 1

            if self.current_count >= self.per_folder:
                self.current_index += 1
                self.current_count = 0

            return folder_name, dest_path

    # ── 매핑 JSON 저장 ──

    def save_mapping(self):
        with self.lock:
            snapshot = dict(self.mapping)
        with open(self.mapping_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

    def get_status_str(self):
        with self.lock:
            folder_name = f"{self.base_name}-{self.current_index:03d}"
            return f"현재폴더:{folder_name}({self.current_count}/{self.per_folder})"


# ──────────────────────────────────────────────
# 통계
# ──────────────────────────────────────────────
class DownloadStats:
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
        speed = self.total_bytes / elapsed / 1024 / 1024 if elapsed > 0 else 0
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


# ──────────────────────────────────────────────
# 데이터 로드
# ──────────────────────────────────────────────
def load_required_video_ids(filepath="all_required_video_ids.txt"):
    with open(filepath, "r") as f:
        return [line.strip() for line in f if line.strip()]


def load_url_mapping(filepath="youtube_id_to_urls_mapping.json"):
    with open(filepath, "r") as f:
        return json.load(f)


# ──────────────────────────────────────────────
# 다운로드 (임시 폴더로)
# ──────────────────────────────────────────────
def download_video(video_id, youtube_url, temp_dir, timeout=120):
    """
    yt-dlp로 비디오를 temp_dir에 다운로드.
    성공 시 temp_dir/{video_id}.mp4 파일이 생성됨.
    """
    output_path = os.path.join(temp_dir, f"{video_id}.mp4")
    temp_path = os.path.join(temp_dir, f"{video_id}.%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/bestvideo[height<=480]+bestaudio/best[height<=480]/best",
        "--merge-output-format", "mp4",
        "-o", temp_path,
        "--no-warnings",
        "-q",
        "--no-progress",
        "--retries", "2",
        "--fragment-retries", "2",
        "--buffer-size", "16K",
        "--no-overwrites",
        "--no-write-info-json",
        "--no-write-thumbnail",
        "--no-write-description",
        youtube_url,
    ]

    if FFMPEG_PATH:
        cmd.insert(1, "--ffmpeg-location")
        cmd.insert(2, os.path.dirname(FFMPEG_PATH))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

        # 다운로드된 파일 확인
        actual_path = None
        for ext in [".mp4", ".mkv", ".webm"]:
            check_path = os.path.join(temp_dir, f"{video_id}{ext}")
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
            stderr = result.stderr.lower() if result.stderr else ""
            if any(kw in stderr for kw in ["unavailable", "private", "removed", "not available"]):
                return {"status": "unavailable", "video_id": video_id, "error": result.stderr}
            return {"status": "failed", "video_id": video_id, "error": result.stderr or "Unknown error"}

    except subprocess.TimeoutExpired:
        for ext in [".mp4", ".mkv", ".webm", ".part", ".ytdl"]:
            temp_file = os.path.join(temp_dir, f"{video_id}{ext}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
        return {"status": "timeout", "video_id": video_id}

    except Exception as e:
        return {"status": "failed", "video_id": video_id, "error": str(e)}


# ──────────────────────────────────────────────
# 출력
# ──────────────────────────────────────────────
def print_progress(stats, total, current, folder_mgr):
    summary = stats.get_summary()
    elapsed = timedelta(seconds=int(summary["elapsed_seconds"]))

    completed = summary["success"] + summary["failed"] + summary["timeout"] + summary["unavailable"]
    if completed > 0:
        rate = completed / summary["elapsed_seconds"]
        remaining = (total - current) / rate if rate > 0 else 0
        eta = timedelta(seconds=int(remaining))
    else:
        eta = "계산중..."

    total_mb = summary["total_bytes"] / 1024 / 1024
    folder_status = folder_mgr.get_status_str()

    print(f"\r[{current}/{total}] "
          f"성공:{summary['success']} "
          f"실패:{summary['failed']} "
          f"타임아웃:{summary['timeout']} "
          f"삭제됨:{summary['unavailable']} "
          f"스킵:{summary['skipped']} | "
          f"{total_mb:.1f}MB | "
          f"{summary['speed_mbps']:.2f}MB/s | "
          f"{folder_status} | "
          f"경과:{elapsed} | ETA:{eta}    ", end="", flush=True)


def save_progress(stats, folder_mgr):
    summary = stats.get_summary()
    with open("download_progress.json", "w") as f:
        json.dump({
            "last_update": datetime.now().isoformat(),
            "stats": summary,
            "errors": stats.errors[-100:],
        }, f, indent=2, ensure_ascii=False)
    folder_mgr.save_mapping()


# ──────────────────────────────────────────────
# main
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Molmo2 YouTube 비디오 다운로드 (폴더 분배)")
    parser.add_argument("--test", action="store_true", help="테스트 모드 (5개만)")
    parser.add_argument("--workers", type=int, default=4, help="병렬 다운로드 수 (기본: 4)")
    parser.add_argument("--timeout", type=int, default=120, help="영상당 최대 다운로드 시간(초) (기본: 120)")
    parser.add_argument("--per-folder", type=int, default=200, help="폴더당 영상 수 (기본: 200)")
    parser.add_argument("--start", type=int, default=0, help="시작 인덱스")
    parser.add_argument("--limit", type=int, default=0, help="최대 다운로드 수 (0=무제한)")
    args = parser.parse_args()

    print("=" * 60)
    print("Molmo2 YouTube 비디오 다운로드 (폴더 분배 버전)")
    print("=" * 60)

    # ── 폴더 매니저 초기화 ──
    folder_mgr = FolderManager(base_name="molmo2-videos", per_folder=args.per_folder)

    # ── 파일 로드 ──
    print("\n필요한 비디오 ID 로드 중...")
    video_ids = load_required_video_ids()
    print(f"총 {len(video_ids):,}개 비디오 필요")

    print("URL 매핑 로드 중...")
    url_mapping = load_url_mapping()

    # ── 다운로드 목록 생성 ──
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

    # ── resume: 이미 받은 파일 스킵 ──
    existing_ids = folder_mgr.load_existing()
    if existing_ids:
        before = len(videos_to_download)
        videos_to_download = [(vid, url) for vid, url in videos_to_download if vid not in existing_ids]
        skipped = before - len(videos_to_download)
        if skipped > 0:
            print(f"이미 다운로드됨 (스킵): {skipped:,}개")

    if not videos_to_download:
        print("\n다운로드할 새 비디오가 없습니다!")
        return

    print(f"실제 다운로드할 비디오: {len(videos_to_download):,}개")
    print(f"\n설정:")
    print(f"  - 워커 수: {args.workers}")
    print(f"  - 타임아웃: {args.timeout}초")
    print(f"  - 폴더당 영상: {args.per_folder}개")
    print(f"  - 최대 해상도: 480p")
    print(f"  - 포맷: mp4")
    print(f"  - 시작 폴더: molmo2-videos-{folder_mgr.current_index:03d} "
          f"({folder_mgr.current_count}개 이미 있음)")

    # ── 통계 / 시그널 ──
    stats = DownloadStats()
    total = len(videos_to_download)

    stop_flag = threading.Event()

    def signal_handler(sig, frame):
        print("\n\n중단 요청됨... 현재 다운로드 완료 후 종료합니다.")
        stop_flag.set()

    signal.signal(signal.SIGINT, signal_handler)

    print(f"\n다운로드 시작...\n")

    # ── 병렬 다운로드 ──
    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}

        for vid_id, url in videos_to_download:
            if stop_flag.is_set():
                break
            future = executor.submit(
                download_video,
                vid_id, url,
                folder_mgr.temp_dir,
                args.timeout,
            )
            futures[future] = vid_id

        for future in as_completed(futures):
            if stop_flag.is_set():
                break

            result = future.result()
            completed += 1

            if result["status"] == "success":
                # 성공: temp -> 서브폴더로 이동
                folder_mgr.assign_file(result["video_id"])
                stats.add_success(result.get("size", 0))
            elif result["status"] == "timeout":
                stats.add_timeout(result["video_id"])
            elif result["status"] == "unavailable":
                stats.add_unavailable(result["video_id"])
            else:
                stats.add_failed(result["video_id"], result.get("error", "Unknown"))

            if completed % 10 == 0 or completed == total:
                print_progress(stats, total, completed, folder_mgr)

            # 매핑 JSON + progress 주기적 저장
            if completed % 100 == 0:
                save_progress(stats, folder_mgr)

    # ── 최종 결과 ──
    # 매핑 JSON 최종 저장
    folder_mgr.save_mapping()

    print("\n\n" + "=" * 60)
    print("다운로드 완료!")
    print("=" * 60)

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

    # 폴더 분배 현황
    folder_counts = defaultdict(int)
    for folder_name in folder_mgr.mapping.values():
        folder_counts[folder_name] += 1
    print(f"\n[폴더 분배]")
    for fname in sorted(folder_counts):
        print(f"  {fname}: {folder_counts[fname]}개")
    print(f"  매핑 파일: {folder_mgr.mapping_path}")

    # 에러 목록 저장
    if stats.errors:
        error_file = "download_errors.txt"
        with open(error_file, "w") as f:
            for vid_id, error in stats.errors:
                f.write(f"{vid_id}\t{error}\n")
        print(f"\n에러 목록 저장됨: {error_file}")

    save_progress(stats, folder_mgr)
    print(f"진행 상황 저장됨: download_progress.json")

    # temp 폴더 정리 (비어있으면 삭제)
    try:
        if not os.listdir(folder_mgr.temp_dir):
            os.rmdir(folder_mgr.temp_dir)
            print(f"임시 폴더 삭제됨: {folder_mgr.temp_dir}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
