#!/usr/bin/env bash
set -euo pipefail
MODELS_DIR="${MODELS_DIR:-/workspace/models}"
files=(
  "diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors"
  "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
  "vae/minimax_h3_video_vae_fp16.safetensors"
  "vae/minimax_h3_audio_vae_fp32.safetensors"
  "loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"
)
missing=0
for f in "${files[@]}"; do
  if [ -s "$MODELS_DIR/$f" ]; then
    printf "OK      %s\n" "$f"
  else
    printf "MISSING %s\n" "$f"
    missing=1
  fi
done
exit "$missing"
