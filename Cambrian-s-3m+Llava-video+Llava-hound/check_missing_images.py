#!/usr/bin/env python3
"""
이미지 파일 존재 여부를 확인하는 스크립트
JSON 또는 JSONL 파일을 읽어서 이미지 경로를 확인하고, 
존재하지 않는 이미지 파일명을 텍스트 파일에 저장합니다.

# Cambrian-Alignment 2.5M 데이터셋 이미지 누락 검사
python check_missing_images.py \
  --json_path /mnt/datasets/Cambrian-Alignment/jsons/alignment_2.5m.jsonl \
  --root_folder /mnt/datasets/Cambrian-Alignment \
  --output missing_Cambrian-Alignment.jsonl \
  --output2 missing_image_place_Cambrian-Alignment.jsonl


# Cambrian-10M (7M with system prompt) 데이터셋 이미지 누락 검사
python check_missing_images.py \
  --json_path /mnt/datasets/Cambrian-10M/jsons/Cambrian7M_withsystemprompt.jsonl \
  --root_folder /mnt/datasets/Cambrian-10M \
  --output missing_Cambrian-10M.json \
  --output2 missing_image_place_Cambrian-10M.json

"""

import argparse
import json
import os
from pathlib import Path
from tqdm import tqdm


def load_data(json_path):
    """JSON 또는 JSONL 파일을 로드합니다."""
    data_list = []
    
    with open(json_path, 'r', encoding='utf-8') as f:
        # 파일 확장자로 JSON/JSONL 구분
        if json_path.endswith('.jsonl'):
            # JSONL 형식: 각 줄이 하나의 JSON 객체
            for line in f:
                line = line.strip()
                if line:
                    data_list.append(json.loads(line))
        else:
            # JSON 형식: 전체 파일이 하나의 JSON (리스트 또는 객체)
            data = json.load(f)
            if isinstance(data, list):
                data_list = data
            else:
                data_list = [data]
    
    return data_list


def check_missing_images(json_path, root_folder, output_file='missing_images.json'):
    """
    JSON 파일의 이미지 경로를 확인하고 존재하지 않는 이미지를 기록합니다.
    
    Args:
        json_path: JSON 또는 JSONL 파일 경로
        root_folder: 이미지 파일들의 루트 폴더 경로
        output_file: 누락된 이미지가 포함된 라인 전체를 저장할 JSON 파일
    """
    print(f"JSON 파일 로딩 중: {json_path}")
    datas = load_data(json_path)
    print(f"총 {len(datas)}개의 데이터 항목을 찾았습니다.")
    
    missing_lines = []
    no_image_key_count = 0
    
    # tqdm으로 진행 상황 표시
    for data in tqdm(datas, desc="이미지 확인 중", unit="개"):
        if 'image' not in data:
            no_image_key_count += 1
            continue
        
        img_path = data['image']
        full_img_path = os.path.join(root_folder, img_path)
        
        # 이미지 파일 존재 여부 확인
        if not os.path.exists(full_img_path):
            # 전체 라인을 JSON 형식으로 저장
            missing_lines.append(json.dumps(data, ensure_ascii=False))
    
    # 결과 저장
    if missing_lines:
        with open(output_file, 'w', encoding='utf-8') as f:
            for line in missing_lines:
                f.write(f"{line}\n")
        
        print(f"\n총 {len(missing_lines)}개의 이미지가 누락되었습니다.")
        print(f"누락된 이미지가 포함된 라인들이 '{output_file}'에 저장되었습니다.")
    else:
        print("\n모든 이미지 파일이 존재합니다! ✓")
    
    # 통계 출력
    total = len(datas)
    found = total - len(missing_lines) - no_image_key_count
    print(f"\n=== 결과 요약 ===")
    print(f"전체 항목: {total}개")
    print(f"존재하는 이미지: {found}개")
    print(f"누락된 이미지: {len(missing_lines)}개")
    if no_image_key_count > 0:
        print(f"경고! 이미지 파일 없음 ('image' 키 없음): {no_image_key_count}개")


def check_missing_image_placeholder(json_path, output_file='missing_image_place.json'):
    """
    이미지가 있는데 대화에 <image> 플레이스홀더가 없는 항목을 찾습니다.
    
    Args:
        json_path: JSON 또는 JSONL 파일 경로
        output_file: <image> 플레이스홀더가 누락된 라인을 저장할 JSON 파일
    """
    print(f"\n<image> 플레이스홀더 확인 중...")
    datas = load_data(json_path)
    
    missing_placeholder_lines = []
    
    for data in tqdm(datas, desc="<image> 플레이스홀더 확인 중", unit="개"):
        text_only = False
        
        # 'image' 키가 없으면 text_only
        if 'image' not in data:
            text_only = True
        
        # text_only가 False인 경우만 체크 (이미지가 있는 경우)
        if not text_only:
            # conversations 확인
            if 'conversations' in data and len(data['conversations']) > 0:
                # 첫 번째 대화의 value 가져오기
                first_conv = data['conversations'][0]
                if 'value' in first_conv:
                    human_query = first_conv['value']
                    
                    # <image> 플레이스홀더가 없는 경우
                    if '<image>' not in human_query:
                        missing_placeholder_lines.append(json.dumps(data, ensure_ascii=False))
    
    # 결과 저장
    if missing_placeholder_lines:
        with open(output_file, 'w', encoding='utf-8') as f:
            for line in missing_placeholder_lines:
                f.write(f"{line}\n")
        
        print(f"\n총 {len(missing_placeholder_lines)}개의 항목에서 <image> 플레이스홀더가 누락되었습니다.")
        print(f"누락된 항목들이 '{output_file}'에 저장되었습니다.")
    else:
        print("\n모든 이미지 항목에 <image> 플레이스홀더가 포함되어 있습니다! ✓")


def main():
    parser = argparse.ArgumentParser(
        description="JSON/JSONL 파일의 이미지 경로를 확인하고 누락된 파일을 찾습니다."
    )
    
    parser.add_argument(
        '--json_path',
        type=str,
        required=True,
        help='JSON 또는 JSONL 파일 경로'
    )
    
    parser.add_argument(
        '--root_folder',
        type=str,
        required=True,
        help='이미지 파일들의 루트 폴더 경로'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='missing_images.json',
        help='누락된 이미지가 포함된 전체 라인을 저장할 파일명 (기본값: missing_images.json)'
    )

    parser.add_argument(
        '--output2',
        type=str,
        default='missing_image_place.json',
        help='누락된 이미지가 포함된 전체 라인을 저장할 파일명 (기본값: missing_images.json)'
    )
    
    args = parser.parse_args()
    
    # 입력 검증
    if not os.path.exists(args.json_path):
        print(f"오류: JSON 파일을 찾을 수 없습니다: {args.json_path}")
        return
    
    if not os.path.exists(args.root_folder):
        print(f"오류: 루트 폴더를 찾을 수 없습니다: {args.root_folder}")
        return
    
    # 메인 실행
    check_missing_images(args.json_path, args.root_folder, args.output)
    
    # <image> 플레이스홀더 확인
    check_missing_image_placeholder(args.json_path, args.output2)


if __name__ == "__main__":
    main()