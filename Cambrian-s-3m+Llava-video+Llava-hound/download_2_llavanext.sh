#!/bin/bash

# Configuration
PATH_TO_LOCAL_DATASET="./"  # 🚨🚨🚨🚨🚨
LOG_FILE="$PATH_TO_LOCAL_DATASET/download_extract_$(date +%Y%m%d_%H%M%S).log"

# Start script recording if not already running under script
if [ -z "$SCRIPT_RUNNING" ]; then
    export SCRIPT_RUNNING=1
    exec script -f -q "$LOG_FILE" -c "$0 $*"
fi

if [ ! -d "LLaVA-Video-178K" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Downloading LLaVA-Video-178K..."
    hf download lmms-lab/LLaVA-Video-178K --repo-type dataset --local-dir LLaVA-Video-178K
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] LLaVA-Video-178K directory already exists"
fi

cd LLaVA-Video-178K
find . -name "*.tar.gz" -exec tar -zxf {} \;

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === All done! ==="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Log saved to: $LOG_FILE"