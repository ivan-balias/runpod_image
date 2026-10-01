# RunPod template settings

Suggested values:

- Container image: your registry image, e.g. `ghcr.io/USER/comfy-h3-story:latest`
- HTTP port: `8188`
- Volume mount path: `/workspace`
- Container disk: ~20-30 GB (image/code only)
- Persistent/network volume: start around 80-120 GB; increase if keeping outputs
- GPU: choose based on H3 VRAM requirement/performance testing

Environment variables:

- `DOWNLOAD_MODELS=1`
- `DOWNLOAD_H3_FL2V_4STEP_LORA=1`
- optional `HF_TOKEN=...`

First boot downloads the missing models to `/workspace/models`.
Later Pods using the same persistent volume skip those downloads.
