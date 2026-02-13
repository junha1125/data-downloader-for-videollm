#!/bin/bash

# Configuration
PATH_TO_LOCAL_DATASET="./"  # 🚨🚨🚨🚨🚨
LOG_FILE="$PATH_TO_LOCAL_DATASET/download_extract_$(date +%Y%m%d_%H%M%S).log"

# Start script recording if not already running under script
if [ -z "$SCRIPT_RUNNING" ]; then
    export SCRIPT_RUNNING=1
    exec script -f -q "$LOG_FILE" -c "$0 $*"
fi

# Step 3: Download and extract LLaVA-Hound
# echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 3: Processing LLaVA-Hound..."
# cd "$PATH_TO_LOCAL_DATASET"

# if [ ! -d "train_video_and_instruction" ]; then
#     echo "[$(date '+%Y-%m-%d %H:%M:%S')] Downloading LLaVA-Hound..."
#     hf download ShareGPTVideo/train_video_and_instruction --repo-type dataset --local-dir train_video_and_instruction
# else
#     echo "[$(date '+%Y-%m-%d %H:%M:%S')] train_video_and_instruction directory already exists"
# fi

# cd train_video_and_instruction/train_300k
# find . -name "*.tar.gz" -exec tar -zxf {} \;

# Step 4: Create Symlinks
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 4: Creating symlinks..."
cd "$PATH_TO_LOCAL_DATASET/Cambrian-S-3M"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Linking LLaVA-Video-178K files..."
ln -sf "$PATH_TO_LOCAL_DATASET/LLaVA-Video-178K"/* ./

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Linking LLaVA-Hound frames..."
mkdir -p shareVideoGPTV/frames
ln -sf "$PATH_TO_LOCAL_DATASET/train_video_and_instruction/train_300k" ./shareVideoGPTV/frames/all_frames

# Step 5: Verify Installation
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 5: Running sanity check..."
cd "$PATH_TO_LOCAL_DATASET/Cambrian-S-3M"
if [ -f "sanity_check.py" ]; then
    python sanity_check.py
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Warning: sanity_check.py not found"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === All done! ==="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Log saved to: $LOG_FILE"