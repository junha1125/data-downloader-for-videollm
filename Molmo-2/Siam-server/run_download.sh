#!/bin/bash
#
# YouTube 다운로드 자동 실행 스크립트
#
# 기능:
# - 200개 성공(~20GB) 단위로 다운로드 반복
# - 한국시간 23:00~06:00에는 휴식 없이 계속
# - 그 외 시간에는 REST_MINUTES 분 휴식 후 재개
#
# 사용법:
#   ./run_download.sh
#   ./run_download.sh --target-gb 10   # 회당 100개 성공 (~10GB)
#   ./run_download.sh --workers 8      # 워커 8개
#

# 기본 설정
TARGET_GB=20
WORKERS=4
TIMEOUT=120
REST_MINUTES=1

# 인자 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --target-gb)
            TARGET_GB="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --rest)
            REST_MINUTES="$2"
            shift 2
            ;;
        *)
            echo "알 수 없는 옵션: $1"
            exit 1
            ;;
    esac
done

# 스크립트 디렉토리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 한국시간(UTC+9) 기준 야간 시간대 체크
# 23:00 ~ 06:00 -> true (휴식 불필요)
is_night_time_kst() {
    # 한국시간 (UTC+9)
    hour=$(TZ="Asia/Seoul" date +%H)
    hour=$((10#$hour))  # 08 같은 octal 문제 방지

    if [[ $hour -ge 23 || $hour -lt 6 ]]; then
        return 0  # true: 야간
    else
        return 1  # false: 주간
    fi
}

# 현재 시간 출력 (한국시간)
print_kst_time() {
    TZ="Asia/Seoul" date "+%Y-%m-%d %H:%M:%S KST"
}

# 남은 대기 비디오 수 확인
get_pending_count() {
    if [[ -f "download_logs/pending_videos.txt" ]]; then
        grep -c . "download_logs/pending_videos.txt" 2>/dev/null || echo 0
    else
        echo 0
    fi
}

# 마지막 라운드 성공 수 확인 (download_state.json에서)
get_last_success_count() {
    if [[ -f "download_logs/download_state.json" ]]; then
        python3 -c "import json; print(json.load(open('download_logs/download_state.json')).get('success', 0))" 2>/dev/null || echo 0
    else
        echo 0
    fi
}

# 시작 메시지
echo "=========================================="
echo "  YouTube 다운로드 자동 실행 스크립트"
echo "=========================================="
echo "시작 시간: $(print_kst_time)"
echo "설정:"
echo "  - 회당 목표: $((TARGET_GB * 10))개 성공 (~${TARGET_GB}GB)"
echo "  - 워커 수: ${WORKERS}"
echo "  - 타임아웃: ${TIMEOUT}초"
echo "  - 휴식 시간: ${REST_MINUTES}분 (야간 제외)"
echo ""

# 로그 디렉토리 확인
if [[ ! -d "download_logs" ]]; then
    echo "로그 디렉토리가 없습니다. 먼저 초기화하세요:"
    echo "  python download_manager.py --init"
    exit 1
fi

# 대기 목록 확인
pending=$(get_pending_count)
if [[ $pending -eq 0 ]]; then
    echo "대기 중인 비디오가 없습니다."
    echo "초기화가 필요하면: python download_manager.py --init"
    exit 0
fi

echo "대기 중인 비디오: ${pending}개"
echo ""

# 라운드 카운터
round=1

# 메인 루프
while true; do
    echo "=========================================="
    echo "라운드 $round 시작 - $(print_kst_time)"
    echo "=========================================="

    # 다운로드 전 대기 비디오 수
    before_pending=$(get_pending_count)

    if [[ $before_pending -eq 0 ]]; then
        echo "모든 다운로드 완료!"
        break
    fi

    echo "대기 중: ${before_pending}개"
    echo ""

    # 다운로드 실행
    python download_manager.py --download \
        --target-gb "$TARGET_GB" \
        --workers "$WORKERS" \
        --timeout "$TIMEOUT"

    # 이번 라운드 성공 수 확인
    success_count=$(get_last_success_count)
    after_pending=$(get_pending_count)

    echo ""
    echo "라운드 $round 완료"
    echo "  성공: ${success_count}개"
    echo "  남은 대기: ${after_pending}개"

    # 더 이상 다운로드할 것이 없으면 종료
    if [[ $after_pending -eq 0 ]]; then
        echo ""
        echo "=========================================="
        echo "모든 다운로드 완료!"
        echo "종료 시간: $(print_kst_time)"
        echo "=========================================="
        break
    fi

    # 성공한 다운로드가 없으면 대기 후 재시도
    if [[ $success_count -eq 0 ]]; then
        echo ""
        echo "경고: 이번 라운드에서 성공한 다운로드가 없습니다."
        echo "10분 후 재시도합니다..."
        sleep 10m
        round=$((round + 1))
        continue
    fi

    # 야간 시간대 체크
    if is_night_time_kst; then
        echo ""
        echo "야간 시간대(23:00~06:00 KST) - 휴식 없이 계속"
    else
        echo ""
        echo "주간 시간대 - ${REST_MINUTES}분 휴식"
        echo "재개 예정: $(TZ="Asia/Seoul" date -d "+${REST_MINUTES} minutes" "+%H:%M:%S KST")"
        sleep "${REST_MINUTES}m"
    fi

    round=$((round + 1))
    echo ""
done

# 최종 상태
echo ""
echo "=========================================="
echo "최종 상태:"
python download_manager.py --status
echo "=========================================="
