#!/usr/bin/env python3
"""
YouTube 비디오 다운로드 매니저

기능:
- 폴더당 100개 파일 제한 (자동 폴더 생성)
- 다운로드 로그 관리 (대기/완료)
- video_id -> 폴더 매핑 JSON 관리
- 20GB 단위 다운로드 후 휴식 신호

사용법:
    # 첫 실행 (로그 초기화)
    python download_manager.py --init

    # 다운로드 (20GB 또는 지정량만큼)
    python download_manager.py --download --target-gb 20

    # 상태 확인
    python download_manager.py --status
"""

import json
import os
import subprocess
import argparse
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import signal

# 설정
FILES_PER_FOLDER = 100
DEFAULT_TARGET_GB = 20
OUTPUT_BASE_DIR = "molmo2-videos"
LOG_DIR = "download_logs"

# 로그 파일들
PENDING_LOG = os.path.join(LOG_DIR, "pending_videos.txt")
COMPLETED_LOG = os.path.join(LOG_DIR, "completed_videos.txt")
FAILED_LOG = os.path.join(LOG_DIR, "failed_videos.txt")
FOLDER_MAPPING = os.path.join(LOG_DIR, "video_folder_mapping.json")
DOWNLOAD_STATE = os.path.join(LOG_DIR, "download_state.json")


def check_ytdlp():
    """yt-dlp 설치 확인"""
    result = subprocess.run(["which", "yt-dlp"], capture_output=True, text=True)
    if result.returncode != 0:
        print("오류: yt-dlp가 설치되어 있지 않습니다.")
        print("설치: pip install yt-dlp")
        exit(1)


def get_ffmpeg_path():
    """ffmpeg 경로 찾기"""
    result = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


check_ytdlp()
FFMPEG_PATH = get_ffmpeg_path()


class FolderManager:
    """폴더 관리 (100개 파일당 새 폴더)"""

    def __init__(self, base_dir, files_per_folder=FILES_PER_FOLDER):
        self.base_dir = base_dir
        self.files_per_folder = files_per_folder
        self.mapping = self._load_mapping()
        self.lock = threading.Lock()

    def _load_mapping(self):
        """video_id -> folder 매핑 로드"""
        if os.path.exists(FOLDER_MAPPING):
            with open(FOLDER_MAPPING, "r") as f:
                return json.load(f)
        return {}

    def _save_mapping(self):
        """매핑 저장"""
        with open(FOLDER_MAPPING, "w") as f:
            json.dump(self.mapping, f, indent=2)

    def _get_current_folder_info(self):
        """현재 폴더와 파일 수 확인"""
        folder_idx = 0
        while True:
            folder_name = f"batch_{folder_idx:04d}"
            folder_path = os.path.join(self.base_dir, folder_name)

            if not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)
                return folder_name, folder_path, 0

            file_count = len([f for f in os.listdir(folder_path) if f.endswith('.mp4')])
            if file_count < self.files_per_folder:
                return folder_name, folder_path, file_count

            folder_idx += 1

    def get_output_path(self, video_id):
        """video_id에 대한 출력 경로 반환 (매핑은 성공 후에만 저장)"""
        with self.lock:
            # 이미 매핑이 있고 파일도 존재하면 사용
            if video_id in self.mapping:
                folder_name = self.mapping[video_id]
                folder_path = os.path.join(self.base_dir, folder_name)
                file_path = os.path.join(folder_path, f"{video_id}.mp4")
                if os.path.exists(file_path):
                    return file_path, folder_name

            # 새 위치 할당 (아직 매핑에 저장하지 않음)
            folder_name, folder_path, _ = self._get_current_folder_info()
            return os.path.join(folder_path, f"{video_id}.mp4"), folder_name

    def confirm_download(self, video_id, folder_name=None):
        """다운로드 성공 후 매핑 저장"""
        with self.lock:
            if folder_name:
                self.mapping[video_id] = folder_name
            self._save_mapping()

    def find_video(self, video_id):
        """video_id로 폴더 찾기"""
        if video_id in self.mapping:
            folder_name = self.mapping[video_id]
            return os.path.join(self.base_dir, folder_name, f"{video_id}.mp4")
        return None


class DownloadLogger:
    """다운로드 로그 관리"""

    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        self.lock = threading.Lock()

    def init_logs(self, video_ids):
        """로그 초기화 (전체 비디오 목록에서)"""
        # 이미 완료된 것들 로드
        completed = set()
        if os.path.exists(COMPLETED_LOG):
            with open(COMPLETED_LOG, "r") as f:
                completed = set(line.strip() for line in f if line.strip())

        # 실패한 것들도 확인
        failed = set()
        if os.path.exists(FAILED_LOG):
            with open(FAILED_LOG, "r") as f:
                failed = set(line.strip().split('\t')[0] for line in f if line.strip())

        # 대기 목록 = 전체 - 완료 - 실패
        pending = [vid for vid in video_ids if vid not in completed and vid not in failed]

        with open(PENDING_LOG, "w") as f:
            for vid in pending:
                f.write(f"{vid}\n")

        return len(pending), len(completed), len(failed)

    def get_pending(self, limit=None):
        """대기 중인 비디오 목록 반환"""
        if not os.path.exists(PENDING_LOG):
            return []
        with open(PENDING_LOG, "r") as f:
            videos = [line.strip() for line in f if line.strip()]
        return videos[:limit] if limit else videos

    def mark_completed(self, video_id, file_size=0):
        """다운로드 완료 기록"""
        with self.lock:
            with open(COMPLETED_LOG, "a") as f:
                f.write(f"{video_id}\n")
            self._remove_from_pending(video_id)

    def mark_failed(self, video_id, error=""):
        """실패 기록"""
        with self.lock:
            with open(FAILED_LOG, "a") as f:
                f.write(f"{video_id}\t{error}\n")
            self._remove_from_pending(video_id)

    def _remove_from_pending(self, video_id):
        """대기 목록에서 제거"""
        if not os.path.exists(PENDING_LOG):
            return
        with open(PENDING_LOG, "r") as f:
            lines = [l.strip() for l in f if l.strip() and l.strip() != video_id]
        with open(PENDING_LOG, "w") as f:
            f.write("\n".join(lines) + "\n" if lines else "")

    def get_stats(self):
        """통계 반환"""
        pending = len(self.get_pending())
        completed = 0
        failed = 0

        if os.path.exists(COMPLETED_LOG):
            with open(COMPLETED_LOG, "r") as f:
                completed = sum(1 for line in f if line.strip())

        if os.path.exists(FAILED_LOG):
            with open(FAILED_LOG, "r") as f:
                failed = sum(1 for line in f if line.strip())

        return {"pending": pending, "completed": completed, "failed": failed}


def download_video(video_id, youtube_url, output_path, timeout=120):
    """단일 비디오 다운로드"""
    output_dir = os.path.dirname(output_path)
    temp_path = os.path.join(output_dir, f"{video_id}.%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/bestvideo[height<=480]+bestaudio/best[height<=480]/best",
        "--merge-output-format", "mp4",
        "-o", temp_path,
        "--no-warnings", "-q", "--no-progress",
        "--retries", "2", "--fragment-retries", "2",
        "--buffer-size", "16K",
        "--no-overwrites",
        "--no-write-info-json", "--no-write-thumbnail", "--no-write-description",
        youtube_url,
    ]

    if FFMPEG_PATH:
        cmd.insert(1, "--ffmpeg-location")
        cmd.insert(2, os.path.dirname(FFMPEG_PATH))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

        # 파일 확인
        actual_path = None
        for ext in [".mp4", ".mkv", ".webm"]:
            check_path = os.path.join(output_dir, f"{video_id}{ext}")
            if os.path.exists(check_path) and os.path.getsize(check_path) > 10000:
                actual_path = check_path
                break

        if actual_path:
            file_size = os.path.getsize(actual_path)
            if actual_path != output_path:
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(actual_path, output_path)
            return {"status": "success", "video_id": video_id, "size": file_size}
        else:
            stderr = result.stderr.lower() if result.stderr else ""
            if any(kw in stderr for kw in ["unavailable", "private", "removed", "not available"]):
                return {"status": "unavailable", "video_id": video_id, "error": "Video unavailable"}
            return {"status": "failed", "video_id": video_id, "error": result.stderr or "Unknown"}

    except subprocess.TimeoutExpired:
        for ext in [".mp4", ".mkv", ".webm", ".part", ".ytdl"]:
            temp_file = os.path.join(output_dir, f"{video_id}{ext}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
        return {"status": "timeout", "video_id": video_id, "error": "Timeout"}

    except Exception as e:
        return {"status": "failed", "video_id": video_id, "error": str(e)}


def run_download(target_gb=DEFAULT_TARGET_GB, workers=4, timeout=120):
    """지정된 용량만큼 다운로드 (200개 성공 = 20GB 기준)"""
    # 20GB = 200개 성공 기준
    target_success = int(target_gb * 10)  # 1GB = 10개

    # URL 매핑 로드
    with open("youtube_id_to_urls_mapping.json", "r") as f:
        url_mapping = json.load(f)

    logger = DownloadLogger()
    folder_mgr = FolderManager(OUTPUT_BASE_DIR)

    pending = logger.get_pending()
    if not pending:
        print("다운로드할 비디오가 없습니다.")
        return 0

    print(f"대기 중인 비디오: {len(pending):,}개")
    print(f"목표: {target_success}개 성공 (~{target_gb}GB)")

    # 통계
    total_bytes = 0
    success_count = 0
    fail_count = 0
    start_time = time.time()

    stop_flag = threading.Event()

    def signal_handler(sig, frame):
        print("\n중단 요청됨...")
        stop_flag.set()

    signal.signal(signal.SIGINT, signal_handler)

    # 다운로드할 목록 준비
    download_list = []
    for vid in pending:
        if vid in url_mapping and url_mapping[vid].get("youtube_url"):
            download_list.append((vid, url_mapping[vid]["youtube_url"]))

    if not download_list:
        print("다운로드 가능한 비디오 URL이 없습니다.")
        return 0

    print(f"다운로드 시작 (workers: {workers})...")

    download_iter = iter(download_list)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}  # future -> (vid_id, folder_name)

        # 초기 작업 제출 (워커 수만큼)
        for _ in range(workers * 2):
            try:
                vid_id, url = next(download_iter)
                output_path, folder_name = folder_mgr.get_output_path(vid_id)

                # 이미 존재하면 스킵
                if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
                    logger.mark_completed(vid_id)
                    continue

                future = executor.submit(download_video, vid_id, url, output_path, timeout)
                futures[future] = (vid_id, folder_name)
            except StopIteration:
                break

        while futures and not stop_flag.is_set():
            # 완료된 작업 처리
            done_futures = []
            for future in list(futures.keys()):
                if future.done():
                    done_futures.append(future)

            if not done_futures:
                time.sleep(0.1)
                continue

            for future in done_futures:
                vid_id, folder_name = futures.pop(future)
                result = future.result()

                if result["status"] == "success":
                    file_size = result.get("size", 0)
                    total_bytes += file_size
                    success_count += 1
                    logger.mark_completed(vid_id, file_size)
                    folder_mgr.confirm_download(vid_id, folder_name)

                    # 진행 상황 출력
                    total_mb = total_bytes / 1024 / 1024
                    elapsed = time.time() - start_time
                    speed = total_mb / elapsed if elapsed > 0 else 0
                    print(f"\r성공: {success_count}/{target_success} | 실패: {fail_count} | "
                          f"{total_mb/1024:.2f}GB | {speed:.1f}MB/s    ", end="", flush=True)

                    # 목표 도달 체크
                    if success_count >= target_success:
                        print(f"\n\n목표 {target_success}개 성공 도달!")
                        # 남은 작업 취소
                        for f in futures:
                            f.cancel()
                        futures.clear()
                        break
                else:
                    fail_count += 1
                    logger.mark_failed(vid_id, result.get("error", ""))

                # 새 작업 제출 (목표 미달성 시)
                if success_count < target_success and not stop_flag.is_set():
                    try:
                        vid_id, url = next(download_iter)
                        output_path, folder_name = folder_mgr.get_output_path(vid_id)

                        if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
                            logger.mark_completed(vid_id)
                        else:
                            new_future = executor.submit(download_video, vid_id, url, output_path, timeout)
                            futures[new_future] = (vid_id, folder_name)
                    except StopIteration:
                        pass  # 더 이상 대기 목록 없음

    # 최종 결과
    elapsed = time.time() - start_time
    total_gb_done = total_bytes / 1024 / 1024 / 1024

    print(f"\n\n완료!")
    print(f"  다운로드: {total_gb_done:.2f}GB ({success_count}개)")
    print(f"  실패: {fail_count}개")
    print(f"  소요시간: {elapsed/60:.1f}분")

    # 상태 저장
    state = {
        "last_run": datetime.now().isoformat(),
        "downloaded_gb": total_gb_done,
        "success": success_count,
        "failed": fail_count
    }
    with open(DOWNLOAD_STATE, "w") as f:
        json.dump(state, f, indent=2)

    return success_count


def main():
    parser = argparse.ArgumentParser(description="YouTube 다운로드 매니저")
    parser.add_argument("--init", action="store_true", help="로그 초기화")
    parser.add_argument("--download", action="store_true", help="다운로드 실행")
    parser.add_argument("--status", action="store_true", help="상태 확인")
    parser.add_argument("--find", type=str, help="video_id로 파일 위치 찾기")
    parser.add_argument("--target-gb", type=float, default=DEFAULT_TARGET_GB, help="목표 다운로드 용량(GB)")
    parser.add_argument("--workers", type=int, default=4, help="병렬 워커 수")
    parser.add_argument("--timeout", type=int, default=120, help="영상당 타임아웃(초)")
    args = parser.parse_args()

    if args.init:
        print("로그 초기화 중...")
        with open("all_required_video_ids.txt", "r") as f:
            video_ids = [line.strip() for line in f if line.strip()]

        logger = DownloadLogger()
        pending, completed, failed = logger.init_logs(video_ids)

        print(f"전체: {len(video_ids):,}개")
        print(f"  대기: {pending:,}개")
        print(f"  완료: {completed:,}개")
        print(f"  실패: {failed:,}개")

        os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
        print(f"출력 디렉토리: {OUTPUT_BASE_DIR}")

    elif args.download:
        run_download(args.target_gb, args.workers, args.timeout)

    elif args.status:
        logger = DownloadLogger()
        stats = logger.get_stats()
        print("=== 다운로드 상태 ===")
        print(f"  대기: {stats['pending']:,}개")
        print(f"  완료: {stats['completed']:,}개")
        print(f"  실패: {stats['failed']:,}개")

        if os.path.exists(DOWNLOAD_STATE):
            with open(DOWNLOAD_STATE, "r") as f:
                state = json.load(f)
            print(f"\n마지막 실행: {state.get('last_run', 'N/A')}")
            print(f"다운로드량: {state.get('downloaded_gb', 0):.2f}GB")

    elif args.find:
        folder_mgr = FolderManager(OUTPUT_BASE_DIR)
        path = folder_mgr.find_video(args.find)
        if path:
            print(f"위치: {path}")
            print(f"존재: {'예' if os.path.exists(path) else '아니오'}")
        else:
            print(f"'{args.find}' 매핑 없음")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
