# data-downloader-for-videollm
## Image

### Cambrian-10M
```bash
huggingface-cli download nyu-visionx/Cambrian-Alignment --repo-type dataset --local-dir Cambrian-Alignment
cd Cambrian-10M
python merge_tars.py
python extract.py

mv sbu558k/ llava_pretrain
mv mnt/disks/storage/data/pretrain_data/2.5m_v2/allava/ ./
ln -s llava_pretrain/ sbu558k

python check_missing_images.py \
  --json_path Cambrian-Alignment/jsons/alignment_2.5m.jsonl \
  --root_folder Cambrian-Alignment \
  --output missing_Cambrian-Alignment.jsonl \
  --output2 missing_image_place_Cambrian-Alignment.jsonl
# 전체 항목: 2513164개
# 존재하는 이미지: 1878317개
# 누락된 이미지: 634847개

python filter_json.py \
  --origin_json Cambrian-Alignment/jsons/alignment_2.5m.jsonl \
  --missing_json missing_Cambrian-Alignment.jsonl \
  --delete_keys "llava_pretrain,sbu558k" \
  --output Cambrian-Alignment/jsons/alignment_filtered.jsonl
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
```md
**Cambrian-S-3M**
star                 | Videos:   3032 | Res: 420x358 | Dur: 30.0s
EgoTask              | Videos:    172 | Res: 640x480 | Dur: 182.5s
vript_short          | Videos:   8776 | Res: 663x1149 | Dur: 4.8s
vidln                | Videos:  41157 | Res: 759x530 | Dur: 9.5s
favd                 | Videos:  10000 | Res: 1216x718 | Dur: 7.8s
k710                 | Videos:  10000 | Res: 654x447 | Dur: 9.7s
timeit               | Videos:  24807 | Res: 728x454 | Dur: 143.5s
EGTEA                | Videos:     16 | Res: 640x480 | Dur: 677.0s
activitynet          | Videos:  10009 | Res: 512x326 | Dur: 117.2s
sharegpt4o           | Videos:   2111 | Res: 1687x953 | Dur: 23.3s
EgoProceL            | Videos:     18 | Res: 1636x987 | Dur: 621.1s
moviechat            | Videos:    795 | Res: 1354x750 | Dur: 446.7s
textvr               | Videos:   7869 | Res: 392x224 | Dur: 18.1s
ssv2                 | Videos:  40000 | Res: 393x240 | Dur: 3.8s
clevrer              | Videos:  10000 | Res: 480x320 | Dur: 5.1s
nturgbd              | Videos:  27354 | Res: 1920x1080 | Dur: 2.8s
nextqa               | Videos:   3870 | Res: 597x437 | Dur: 44.9s
Ego4d                | Videos:    124 | Res: 1876x1397 | Dur: 21.7s
HoloAssist           | Videos:    121 | Res: 896x504 | Dur: 272.7s
ADL                  | Videos:      8 | Res: 1280x960 | Dur: 1649.7s
IndustReal           | Videos:     44 | Res: 1280x720 | Dur: 242.4s
ChardesEgo           | Videos:    591 | Res: 905x781 | Dur: 30.7s
Ego4d_clip           | Videos:    399 | Res: 1859x1062 | Dur: 22.8s
guiworld             | Videos:  10556 | Res: 1357x931 | Dur: 17.1s
lsmdc                | Videos:  24254 | Res: 1920x1080 | Dur: 4.1s
vript_long           | Videos: 400040 | Res: 1267x718 | Dur: 11.2s
webvid               | Videos:  99922 | Res: 595x334 | Dur: 18.0s
EpicKitchens         | Videos:     36 | Res: 1902x1080 | Dur: 415.1s
youcook2             | Videos:   7783 | Res: 1393x800 | Dur: 19.5s
k400_targz           | Videos: 221966 | Res: 773x505 | Dur: 9.5s

**LLaVA-Video**
gpt4o_caption_prompt | Videos:      1 | Res: 406x720 | Dur: 15.0s
NextQA               | Videos:   3868 | Res: 597x437 | Dur: 44.9s
perception_test      | Videos:   1955 | Res: 1685x951 | Dur: 23.2s
liwei_youtube_videos | Videos: 141889 | Res: 698x675 | Dur: 57.6s
ActivityNet-QA       | Videos:   2353 | Res: 874x543 | Dur: 90.4s
academic_source      | Videos:  30415 | Res: 865x563 | Dur: 48.4s
```

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
# 전체 항목: 3635538개
# 존재하는 이미지: 3370215개
# 누락된 이미지: 265323개

python filter_json.py \
  --origin_json cambrian_s_3m.jsonl \
  --missing_json missing_Cambrian-S.jsonl \
  --delete_keys "tgif,tvqa,htstep_eventcount,htstep_eventunderstanding,htstep_eventrelationship,train_video_and_instruction" \
  --output cambrian_s_3m_filtered.jsonl
#  === 필터링 결과 ===
# 원본 데이터: 3635538개
# 누락된 이미지로 제거: 265323개
# 특정 경로로 제거: 317761개
# 최종 데이터: 3052454개
# 제거된 총 데이터: 583084개

python filter_short_videos.py cambrian_s_3m_filtered.jsonl --output cambrian_s_3m_filtered_over5s.jsonl
# 

python find_image_only_dirs.py # Just analye.
python analyze_videos.py # Just analye. Time consumming (~12H)
# mp4, mkv, web,avi, mov formats

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
...precessing...
```

