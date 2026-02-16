#!/usr/bin/env python3
"""
JSON 파일에서 누락된 이미지와 특정 경로의 데이터를 제거하는 스크립트

python filter_json.py \
  --origin_json /mnt/datasets/Cambrian-Alignment/jsons/alignment_2.5m.jsonl \
  --missing_json /mnt/datasets/missing_Cambrian-Alignment.jsonl \
  --delete_keys "llava_pretrain,sbu558k" \
  --output /mnt/datasets/Cambrian-Alignment/jsons/alignment_filtered.jsonl
"""

#!/usr/bin/env python3
"""
JSON 파일에서 누락된 이미지와 특정 경로의 데이터를 제거하는 스크립트
"""

#!/usr/bin/env python3
"""
JSON 파일에서 누락된 이미지와 특정 경로의 데이터를 제거하는 스크립트
"""

import argparse
import json
import os
from tqdm import tqdm


def load_data(json_path):
    """JSON 또는 JSONL 파일을 로드합니다."""
    data_list = []
    
    with open(json_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        
        if not content:
            return data_list
        
        # 먼저 일반 JSON으로 파싱 시도
        try:
            data = json.loads(content)
            if isinstance(data, list):
                data_list = data
            else:
                data_list = [data]
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 JSONL로 처리
            for line in content.split('\n'):
                line = line.strip()
                if line:
                    try:
                        data_list.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"경고: 라인 파싱 실패: {line[:100]}... - {e}")
                        continue
    
    return data_list


def create_missing_image_set(missing_json_path):
    """missing.json 파일에서 누락된 이미지 경로 집합을 생성합니다."""
    missing_data = load_data(missing_json_path)
    missing_images = set()
    
    for data in missing_data:
        if 'image' in data:
            missing_images.add(data['image'])
    
    print(f"누락된 이미지 {len(missing_images)}개를 로드했습니다.")
    return missing_images


def filter_json(origin_json_path, missing_json_path, delete_keys, output_file='filtered_data.json'):
    """
    원본 JSON에서 누락된 이미지와 특정 경로의 데이터를 제거합니다.
    
    Args:
        origin_json_path: 원본 JSON 또는 JSONL 파일 경로
        missing_json_path: 누락된 이미지 정보가 담긴 JSON 파일 경로
        delete_keys: 삭제할 경로 키워드 리스트
        output_file: 필터링된 결과를 저장할 파일
    """
    print(f"원본 JSON 파일 로딩 중: {origin_json_path}")
    origin_data = load_data(origin_json_path)
    print(f"총 {len(origin_data)}개의 원본 데이터 항목을 로드했습니다.")
    
    # 누락된 이미지 집합 생성
    missing_images = create_missing_image_set(missing_json_path)
    
    # 삭제할 키워드 파싱
    delete_key_list = [key.strip() for key in delete_keys.split(',') if key.strip()]
    print(f"삭제할 경로 키워드: {delete_key_list}")
    
    # 필터링
    filtered_data = []
    removed_by_missing = 0
    removed_by_delete_keys = 0
    
    for data in tqdm(origin_data, desc="데이터 필터링 중", unit="개"):
        if 'image' not in data:
            # 이미지가 없는 데이터는 그대로 유지
            filtered_data.append(data)
            continue
        
        img_path = data['image']
        
        # 1. 누락된 이미지인지 확인
        if img_path in missing_images:
            removed_by_missing += 1
            continue
        
        # 2. delete_keys에 해당하는 경로인지 확인
        should_delete = False
        for delete_key in delete_key_list:
            if delete_key in img_path:
                should_delete = True
                removed_by_delete_keys += 1
                break
        
        if should_delete:
            continue
        
        # 필터를 통과한 데이터 추가
        filtered_data.append(data)
    
    # 결과 저장 - 출력 파일 확장자로 형식 결정
    is_jsonl = output_file.endswith('.jsonl')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        if is_jsonl:
            # JSONL 형식으로 저장
            for data in filtered_data:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        else:
            # JSON 형식으로 저장
            json.dump(filtered_data, f, ensure_ascii=False, indent=2)
    
    # 통계 출력
    print(f"\n=== 필터링 결과 ===")
    print(f"원본 데이터: {len(origin_data)}개")
    print(f"누락된 이미지로 제거: {removed_by_missing}개")
    print(f"특정 경로로 제거: {removed_by_delete_keys}개")
    print(f"최종 데이터: {len(filtered_data)}개")
    print(f"제거된 총 데이터: {len(origin_data) - len(filtered_data)}개")
    print(f"\n필터링된 데이터가 '{output_file}'에 저장되었습니다.")


def main():
    parser = argparse.ArgumentParser(
        description="원본 JSON에서 누락된 이미지와 특정 경로의 데이터를 제거합니다."
    )
    
    parser.add_argument(
        '--origin_json',
        type=str,
        required=True,
        help='원본 JSON 또는 JSONL 파일 경로'
    )
    
    parser.add_argument(
        '--missing_json',
        type=str,
        required=True,
        help='누락된 이미지 정보가 담긴 JSON 파일 경로'
    )
    
    parser.add_argument(
        '--delete_keys',
        type=str,
        required=True,
        help='삭제할 경로 키워드 (쉼표로 구분, 예: "llava_pretrain,sbu558k")'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='filtered_data.json',
        help='필터링된 데이터를 저장할 파일명 (기본값: filtered_data.json)'
    )
    
    args = parser.parse_args()
    
    # 입력 검증
    if not os.path.exists(args.origin_json):
        print(f"오류: 원본 JSON 파일을 찾을 수 없습니다: {args.origin_json}")
        return
    
    if not os.path.exists(args.missing_json):
        print(f"오류: missing JSON 파일을 찾을 수 없습니다: {args.missing_json}")
        return
    
    # 메인 실행
    filter_json(args.origin_json, args.missing_json, args.delete_keys, args.output)


if __name__ == "__main__":
    main()