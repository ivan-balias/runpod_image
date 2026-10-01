#!/usr/bin/env bash
set -euo pipefail

MODELS_DIR="${MODELS_DIR:-/workspace/models}"
REPO="${H3_REPO:-Comfy-Org/MiniMax-H3}"

mkdir -p \
  "$MODELS_DIR/diffusion_models" \
  "$MODELS_DIR/text_encoders" \
  "$MODELS_DIR/vae" \
  "$MODELS_DIR/loras"

# hf honors HF_TOKEN/HUGGING_FACE_HUB_TOKEN when supplied.
# --local-dir preserves the repository folder layout directly under models/.
download_file() {
  local remote="$1"
  local local_path="$MODELS_DIR/$remote"

  if [ -s "$local_path" ]; then
    echo "[models] OK   $remote"
    return 0
  fi

  echo "[models] GET  $remote"
  hf download "$REPO" "$remote" --local-dir "$MODELS_DIR"

  if [ ! -s "$local_path" ]; then
    echo "[models] ERROR: expected file missing after download: $local_path" >&2
    exit 1
  fi
}

# ---- Required H3 FL2VA stack ----
download_file "diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors"
download_file "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
download_file "vae/minimax_h3_video_vae_fp16.safetensors"
download_file "vae/minimax_h3_audio_vae_fp32.safetensors"

# ---- Recommended speed LoRA ----
if [ "${DOWNLOAD_H3_FL2V_4STEP_LORA:-0}" = "1" ]; then
  download_file "loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"
fi

# ---- Optional LoRAs ----
if [ "${DOWNLOAD_H3_FL2V_8STEP_LORA:-0}" = "1" ]; then
  download_file "loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors"
fi

if [ "${DOWNLOAD_H3_REF2V_4STEP_LORA:-0}" = "1" ]; then
  download_file "loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors"
fi

echo "[models] H3 model set is ready in $MODELS_DIR"
