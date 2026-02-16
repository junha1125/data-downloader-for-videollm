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
  --output missing_Cambrian-Alignment.json \
  --output2 missing_image_place_Cambrian-Alignment.json
python filter_json.py \
  --origin_json Cambrian-Alignment/jsons/alignment_2.5m.jsonl \
  --missing_json missing_Cambrian-Alignment.jsonl \
  --delete_keys "llava_pretrain,sbu558k" \ # optional
  --output Cambrian-Alignment/jsons/alignment_filtered.jsonl
```

### Cambrian-10M
```bash
huggingface-cli download nyu-visionx/Cambrian-10M --repo-type dataset --local-dir Cambrian-10M
cd Cambrian-10M
python merge_tars.py
python extract.py
```


## Video
### Cambrian-S-3M
```bash
cd ./Cambrian-s-3m+Llava-video+Llava-hound
bash ./download_1_cambrian-s-3m.sh
```


### LLaVA-Video
```bash
cd ./Cambrian-s-3m+Llava-video+Llava-hound
bash ./download_2_llavanext.sh
```


<!-- ### LLaVA-Hound
```bash
cd ./Cambrian-s-3m+Llava-video+Llava-hound
bash ./download_3_llavahound.sh
``` -->

### SynLinking
```bash
cd ./Cambrian-s-3m+Llava-video+Llava-hound
bash ./download_4_laststep.sh
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

