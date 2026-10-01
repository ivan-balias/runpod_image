#!/usr/bin/env bash
set -euo pipefail

COMFYUI_DIR="${COMFYUI_DIR:-/opt/ComfyUI}"
WORKSPACE="${WORKSPACE:-/workspace}"

mkdir -p \
  "$WORKSPACE/models" \
  "$WORKSPACE/input" \
  "$WORKSPACE/output" \
  "$WORKSPACE/user" \
  "$WORKSPACE/.cache/huggingface"

# Keep large/changing data on persistent storage.
for name in models input output user; do
  target="$WORKSPACE/$name"
  link="$COMFYUI_DIR/$name"
  if [ -e "$link" ] && [ ! -L "$link" ]; then
    rm -rf "$link"
  fi
  ln -sfn "$target" "$link"
done

# Download only files that are missing. Disable with DOWNLOAD_MODELS=0.
if [ "${DOWNLOAD_MODELS:-1}" = "1" ]; then
  /opt/story-scripts/download_models.sh
fi

# Copy bundled workflows only once; never overwrite user edits.
# Keep a plain workspace copy and also expose them in ComfyUI's user workflow folder.
mkdir -p "$WORKSPACE/workflows"
mkdir -p "$WORKSPACE/user/default/workflows"
cp -n /opt/story-workflows/* "$WORKSPACE/workflows/" 2>/dev/null || true
cp -n /opt/story-workflows/*.json "$WORKSPACE/user/default/workflows/" 2>/dev/null || true

echo "============================================================"
echo "ComfyUI H3 story workload"
echo "ComfyUI:      $COMFYUI_DIR"
echo "Workspace:    $WORKSPACE"
echo "Models:       $WORKSPACE/models"
echo "Outputs:      $WORKSPACE/output"
echo "Web port:     8188"
echo "============================================================"

cd "$COMFYUI_DIR"
exec python3 main.py \
  --listen 0.0.0.0 \
  --port 8188 \
  ${COMFYUI_ARGS:-}
