#!/bin/bash

# Configuration
PATH_TO_LOCAL_DATASET="./"  # 🚨🚨🚨🚨🚨 나중에 멀티 쓰레드 코드로 바꿔서 돌리기 이거 너무 느림
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
    name_without_ext="${file%.tar.zst}"
    dirname=$(echo "$name_without_ext" | sed 's/_[0-9]*$//')
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Extracting $file -> $dirname/..."
    mkdir -p "$dirname"
    tar -I zstd -xf "$file" -C "$dirname"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deleting $file..."
    rm -f "$file"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deleted $file"
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === All done! ==="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Log saved to: $LOG_FILE"