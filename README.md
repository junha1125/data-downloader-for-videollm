# data-downloader-for-videollm
## Image

### Cambrian-Alignment
```bash
huggingface-cli download nyu-visionx/Cambrian-Alignment --repo-type dataset --local-dir Cambrian-Alignment
cd Cambrian-Alignment
python merge_tars.py
python extract.py

mv sbu558k/ llava_pretrain
cd llava_pretrain && mkdir images
mv mnt/disks/storage/data/pretrain_data/2.5m_v2/allava/ ./
ln -s llava_pretrain/images sbu558k

python check_missing_images.py \
  --json_path Cambrian-Alignment/jsons/alignment_2.5m.jsonl \
  --root_folder Cambrian-Alignment \
  --output missing_Cambrian-Alignment.jsonl \
  --output2 missing_image_place_Cambrian-Alignment.jsonl
# 📝결과
# 전체 항목: 2513164개
# 존재하는 이미지: 1878317개
# 누락된 이미지: 634847개

python filter_json.py \
  --origin_json Cambrian-Alignment/jsons/alignment_2.5m.jsonl \
  --missing_json missing_Cambrian-Alignment.jsonl \
  --delete_keys "sbu558k" \
  --output Cambrian-Alignment/jsons/alignment_filtered.jsonl
# 📝결과
# 원본 데이터: 2513164개
# 누락된 이미지로 제거: 634847개
# 특정 경로로 제거: 558128개
# 최종 데이터: 1320189개
# 제거된 총 데이터: 1192975개
```

### Cambrian-10M
```bash
huggingface-cli download nyu-visionx/Cambrian-10M --repo-type dataset --local-dir Cambrian-10M
cd Cambrian-10M
python merge_tars.py
python extract.py

python check_missing_images.py \
  --json_path /mnt/datasets/Cambrian-10M/jsons/Cambrian7M_withsystemprompt.jsonl \
  --root_folder /mnt/datasets/Cambrian-10M \
  --output missing_Cambrian-10M.jsonl \
  --output2 missing_image_place_Cambrian-10M.json
## No filetering was required
```


## Video

> **Cambrian-S-3M**

| Dataset        | Videos | Resolution   | Duration (s) |
|---------------|--------|--------------|--------------|
| star          | 3032   | 420x358      | 30.0         |
| EgoTask       | 172    | 640x480      | 182.5        |
| vript_short   | 8776   | 663x1149     | 4.8          |
| vidln         | 41157  | 759x530      | 9.5          |
| favd          | 10000  | 1216x718     | 7.8          |
| k710          | 10000  | 654x447      | 9.7          |
| timeit        | 24807  | 728x454      | 143.5        |
| EGTEA         | 16     | 640x480      | 677.0        |
| activitynet   | 10009  | 512x326      | 117.2        |
| sharegpt4o    | 2111   | 1687x953     | 23.3         |
| EgoProceL     | 18     | 1636x987     | 621.1        |
| moviechat     | 795    | 1354x750     | 446.7        |
| textvr        | 7869   | 392x224      | 18.1         |
| ssv2          | 40000  | 393x240      | 3.8          |
| clevrer       | 10000  | 480x320      | 5.1          |
| nturgbd       | 27354  | 1920x1080    | 2.8          |
| nextqa        | 3870   | 597x437      | 44.9         |
| Ego4d         | 124    | 1876x1397    | 21.7         |
| HoloAssist    | 121    | 896x504      | 272.7        |
| ADL           | 8      | 1280x960     | 1649.7       |
| IndustReal    | 44     | 1280x720     | 242.4        |
| ChardesEgo    | 591    | 905x781      | 30.7         |
| Ego4d_clip    | 399    | 1859x1062    | 22.8         |
| guiworld      | 10556  | 1357x931     | 17.1         |
| lsmdc         | 24254  | 1920x1080    | 4.1          |
| vript_long    | 400040 | 1267x718     | 11.2         |
| webvid        | 99922  | 595x334      | 18.0         |
| EpicKitchens  | 36     | 1902x1080    | 415.1        |
| youcook2      | 7783   | 1393x800     | 19.5         |
| k400_targz    | 221966 | 773x505      | 9.5          |

> **LLaVA-Video**

| Dataset                | Videos | Resolution   | Duration (s) |
|------------------------|--------|--------------|--------------|
| gpt4o_caption_prompt   | 1      | 406x720      | 15.0         |
| NextQA                 | 3868   | 597x437      | 44.9         |
| perception_test        | 1955   | 1685x951     | 23.2         |
| liwei_youtube_videos   | 141889 | 698x675      | 57.6         |
| ActivityNet-QA         | 2353   | 874x543      | 90.4         |
| academic_source        | 30415  | 865x563      | 48.4         |


### Cambrian-S-3M
```bash
cd ./Cambrian-s-3m+Llava-video+Llava-hound
bash ./download_1_cambrian-s-3m.sh
# or python Siam-server/download_part_Cambrian-S-3M.py --sample-ratio 1.0 ...
ln -s /mnt/datasets/LLaVA-Video-178K/* ./
rm 0_* 1_* 2_* 30_*


python check_missing_images.py \
  --json_path ./cambrian_s_3m.jsonl \
  --root_folder ./ \
  --output missing_Cambrian-S.jsonl \
  --output2 missing_image_place_Cambrian-S.json
# 📝결과
# 전체 항목: 3635538개
# 존재하는 이미지: 3370215개
# 누락된 이미지: 265323개

python filter_json.py \
  --origin_json cambrian_s_3m.jsonl \
  --missing_json missing_Cambrian-S.jsonl \
  --delete_keys "tgif,tvqa,htstep_eventcount,htstep_eventunderstanding,htstep_eventrelationship,train_video_and_instruction,EpicKitchens" \
  --output cambrian_s_3m_filtered.jsonl
# 📝결과
# 원본 데이터: 3635538개
# 누락된 이미지로 제거: 265323개
# 특정 경로로 제거: 317761개
# 최종 데이터: 3052454개
# 제거된 총 데이터: 583084개
# EpicKitchens 는 영상 길이 및 데이터 퀄리티에 문제 있음

python filter_short_videos.py cambrian_s_3m_filtered.jsonl --output cambrian_s_3m_filtered_over5s.jsonl
# 📝결과
# Total lines : 3,052,454
# Kept (>=5s)  : 2,813,074
# Skipped (<5s): 227,828
# Error        : 11,552 (maybe image only data)

python filter_based_keys.py cambrian_s_3m_filtered_over5s.jsonl --output cambrian_s_3m_filtered_over5s_video.jsonl
# datas with 'audio, <speech> in conversation, image' keys are removed.
# 📝결과
# total:              2,813,074
# Kept:               2,810,976
# Excluded (audio):   2,098
# Excluded (speech):  0
# Excluded (image):   0
# Excluded total:     2,098

python filter_curropted_process_video_durations.py \
  -i cambrian_s_3m_filtered_over5s_video.jsonl \
  -v /mnt/datasets-2/cambrian_s_3m/ \
  --duration-dir /mnt/datasets-2/cambrian_s_3m/duration_json \
  --decord-timeout 60
# decord 로 load 되지 않는 깨진 영상 제거
# 각 영상당 duration 값을 json 에 추가한 새로운 json 파일 저장
# cambrian_s_3m_filtered_over5s_video_with_duration.jsonl saved.

python filter_core_keys.py cambrian_s_3m_filtered_over5s_video_with_duration.jsonl
# datas with 'start_time, end_time, fps, start_frame, end_frame' keys are deleted.

python find_image_only_dirs.py # Just analye.
python analyze_videos.py # Just analye. Time consumming (~12H)
# mp4, mkv, web,avi, mov formats

```


```bash
python print_video_duration_hist.py cambrian_s_3m_filtered_over5s_video_with_duration_core_keys.jsonl 2 10 100
>> 인자 순서: `<jsonl파일> <pivot분> <short%> <long%>`
>> cambrian_s_3m_..._under_2m_10p.jsonl   # 2분 미만, 10% 샘플
>> cambrian_s_3m_..._over_2m_100p.jsonl   # 2분 이상, 100% 전체


=======================================================
  30초 단위 분포
=======================================================
  구간                             데이터 수         비율
  -------------------------------------------
  0s ~ 30s                   1,545,377     59.72%
  30s ~ 60s                    416,537     16.10%
  60s ~ 90s                    164,380      6.35%
  90s ~ 120s                   166,776      6.45%
  120s ~ 150s                  136,287      5.27%
  150s ~ 180s                  128,402      4.96%
  180s ~ 210s                   12,934      0.50%
  210s ~ 240s                    8,133      0.31%
  240s ~ 270s                    1,781      0.07%
  270s ~ 300s                    1,794      0.07%

=======================================================
  5분 단위 분포
=======================================================
  구간                             데이터 수         비율
  -------------------------------------------
  0min ~ 5min                2,582,401     99.80%
  5min ~ 10min                   5,042      0.19%
  10min ~ 15min                    103      0.00%
  15min ~ 20min                     40      0.00%
  20min ~ 25min                      6      0.00%
  25min ~ 30min                     19      0.00%
  30min ~ 35min                      5      0.00%
  35min ~ 40min                      1      0.00%
  40min ~ 45min                      2      0.00%
  45min ~ 50min                      3      0.00%
  50min ~ 55min                      3      0.00%
  55min ~ 60min                      1      0.00%
  60min ~ 65min                      2      0.00%
  65min ~ 70min                      2      0.00%
  80min ~ 85min                      2      0.00%
  115min ~ 120min                    1      0.00%
  -------------------------------------------
  합계                         2,587,633    100.00%
=======================================================
```


### LLaVA-Video
```bash
cd ./Cambrian-s-3m+Llava-video+Llava-hound
bash ./download_2_llavanext.sh

python llava-video/find_image_only_dirs.py # Just analye.
# None
python llava-video/analyze_videos.py # Just analye. Time consumming (~12H)
```

### Molmo-2

**Video only**
Required_file: [youtube_id_to_urls_mapping.json](https://huggingface.co/datasets/allenai/Molmo2-VideoSubtitleQA/blob/main/youtube_id_to_urls_mapping.json)
```bash
cd ./Molmo-2
python count_required_videos.py # >> output: all_required_video_ids.txt
python download_youtube_.py     # Vidoes are stored in folders
```

**Annotaions**
```bash
...updating...
```

