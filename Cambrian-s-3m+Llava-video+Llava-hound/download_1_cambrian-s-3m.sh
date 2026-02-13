#!/bin/bash

# Configuration
PATH_TO_LOCAL_DATASET="./"  # 🚨🚨🚨🚨🚨
LOG_FILE="$PATH_TO_LOCAL_DATASET/download_extract_$(date +%Y%m%d_%H%M%S).log"

# Start script recording if not already running under script
if [ -z "$SCRIPT_RUNNING" ]; then
    export SCRIPT_RUNNING=1
    exec script -f -q "$LOG_FILE" -c "$0 $*"
fi

echo "=== Starting dataset download and extraction ==="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Log file: $LOG_FILE"

# Step 1: Download and extract Cambrian-S-3M
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 1: Processing Cambrian-S-3M..."
cd "$PATH_TO_LOCAL_DATASET"

if [ ! -d "Cambrian-S-3M" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Downloading Cambrian-S-3M..."
    hf download nyu-visionx/Cambrian-S-3M --repo-type dataset --local-dir Cambrian-S-3M
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cambrian-S-3M directory already exists"
fi

cd Cambrian-S-3M
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Decompressing Cambrian-S-3M archives..."
for file in *.tar.zst; do
    [ -e "$file" ] || continue
    dirname="${file%.tar.zst}"
    if [ ! -d "$dirname" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Extracting $file..."
        tar --use-compress-program=unzstd -xvf "$file"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deleting $file..."
        rm -f "$file"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deleted $file"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Skipping $file (already extracted)"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deleting $file..."
        rm -f "$file"
    fi
done

# Step 2: Download and extract LLaVA-Video-178K
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 2: Processing LLaVA-Video-178K..."
cd "$PATH_TO_LOCAL_DATASET"

if [ ! -d "LLaVA-Video-178K" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Downloading LLaVA-Video-178K..."
    hf download lmms-lab/LLaVA-Video-178K --repo-type dataset --local-dir LLaVA-Video-178K
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] LLaVA-Video-178K directory already exists"
fi

# cd LLaVA-Video-178K
# echo "[$(date '+%Y-%m-%d %H:%M:%S')] Decompressing LLaVA-Video-178K archives..."
# find . -name "*.tar.gz" | while read file; do
#     dirname="${file%.tar.gz}"
#     if [ ! -d "$dirname" ]; then
#         echo "[$(date '+%Y-%m-%d %H:%M:%S')] Extracting $file..."
#         tar -zxvf "$file"
#         echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deleting $file..."
#         rm -f "$file"
#         echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deleted $file"
#     else
#         echo "[$(date '+%Y-%m-%d %H:%M:%S')] Skipping $file (already extracted)"
#         echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deleting $file..."
#         rm -f "$file"
#     fi
# done

# # Step 3: Download and extract LLaVA-Hound
# echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 3: Processing LLaVA-Hound..."
# cd "$PATH_TO_LOCAL_DATASET"

# if [ ! -d "train_video_and_instruction" ]; then
#     echo "[$(date '+%Y-%m-%d %H:%M:%S')] Downloading LLaVA-Hound..."
#     hf download ShareGPTVideo/train_video_and_instruction --repo-type dataset --local-dir train_video_and_instruction
# else
#     echo "[$(date '+%Y-%m-%d %H:%M:%S')] train_video_and_instruction directory already exists"
# fi

# cd train_video_and_instruction/train_300k
# echo "[$(date '+%Y-%m-%d %H:%M:%S')] Decompressing LLaVA-Hound archives..."
# find . -name "*.tar.gz" | while read file; do
#     dirname="${file%.tar.gz}"
#     if [ ! -d "$dirname" ]; then
#         echo "[$(date '+%Y-%m-%d %H:%M:%S')] Extracting $file..."
#         tar -zxvf "$file"
#         echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deleting $file..."
#         rm -f "$file"
#         echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deleted $file"
#     else
#         echo "[$(date '+%Y-%m-%d %H:%M:%S')] Skipping $file (already extracted)"
#         echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deleting $file..."
#         rm -f "$file"
#     fi
# done

# # Step 4: Create Symlinks
# echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 4: Creating symlinks..."
# cd "$PATH_TO_LOCAL_DATASET/Cambrian-S-3M"

# echo "[$(date '+%Y-%m-%d %H:%M:%S')] Linking LLaVA-Video-178K files..."
# ln -sf "$PATH_TO_LOCAL_DATASET/LLaVA-Video-178K"/* ./

# echo "[$(date '+%Y-%m-%d %H:%M:%S')] Linking LLaVA-Hound frames..."
# mkdir -p shareVideoGPTV/frames
# ln -sf "$PATH_TO_LOCAL_DATASET/train_video_and_instruction/train_300k" ./shareVideoGPTV/frames/all_frames

# # Step 5: Verify Installation
# echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 5: Running sanity check..."
# cd "$PATH_TO_LOCAL_DATASET/Cambrian-S-3M"
# if [ -f "sanity_check.py" ]; then
#     python sanity_check.py
# else
#     echo "[$(date '+%Y-%m-%d %H:%M:%S')] Warning: sanity_check.py not found"
# fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === All done! ==="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Log saved to: $LOG_FILE"