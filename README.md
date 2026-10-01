# RunPod ComfyUI + MiniMax H3 Story Workload

Starter workload for the scene-chaining video workflow we designed.

## Included

- Current ComfyUI source at Docker build time
- CUDA-enabled PyTorch
- ffmpeg
- ComfyUI-VideoHelperSuite
- `Story Scene Loop` custom node
- Automatic persistent H3 model download
- MiniMax H3 FL2VA pruned INT8 model
- Qwen3-VL 32B NVFP4/AWQ text encoder
- H3 video + audio VAEs
- bundled MiniMax H3 I2V workflow from your ComfyUI export
- optional FL2V 4-step/8-step and Ref2V LoRAs (not downloaded unless enabled)
- `/workspace` persistence layout for RunPod

## Folder layout on the Pod

```text
/workspace/
├── models/
│   ├── diffusion_models/
│   ├── text_encoders/
│   ├── vae/
│   └── loras/
├── input/
├── output/
├── user/
├── workflows/
└── .cache/huggingface/
```

## Build

```bash
docker build -t YOUR_REGISTRY/comfy-h3-story:latest .
docker push YOUR_REGISTRY/comfy-h3-story:latest
```

For GitHub Container Registry:

```bash
docker build -t ghcr.io/YOUR_GITHUB_USER/comfy-h3-story:latest .
docker push ghcr.io/YOUR_GITHUB_USER/comfy-h3-story:latest
```

## RunPod

Create a template using the image and mount persistent/network storage at:

```text
/workspace
```

Expose HTTP port:

```text
8188
```

On first startup the workload downloads only missing H3 files. Future Pods using
the same `/workspace` volume reuse them.

## Model download flags

Default:

```text
DOWNLOAD_MODELS=1
DOWNLOAD_H3_FL2V_4STEP_LORA=0
DOWNLOAD_H3_FL2V_8STEP_LORA=0
DOWNLOAD_H3_REF2V_4STEP_LORA=0
```

To add the 8-step LoRA, set:

```text
DOWNLOAD_H3_FL2V_8STEP_LORA=1
```

To add Ref2V Turbo:

```text
DOWNLOAD_H3_REF2V_4STEP_LORA=1
```

## Check the model volume

Inside the Pod:

```bash
/opt/story-scripts/check_models.sh
```

## Updating the custom node

Replace:

```text
custom_nodes/story_scene_loop/
```

then rebuild/push the Docker image. Models remain on the persistent volume and
are not re-downloaded.

## Important

The MiniMax H3 repository uses the MiniMax H3 Community License. Review its
current terms before commercial/monetized use.

## Bundled H3 workflow

Your supplied workflow is included as:

```text
workflows/minimax_h3_i2v_story_base.json
```

At Pod startup it is copied (without overwriting edits) to both:

```text
/workspace/workflows/minimax_h3_i2v_story_base.json
/workspace/user/default/workflows/minimax_h3_i2v_story_base.json
```

The supplied graph uses the INT8 ConvRot H3 diffusion model, NVFP4/AWQ Qwen3-VL encoder, video VAE and audio VAE. It does **not** contain a LoRA loader, so Turbo LoRAs are opt-in rather than downloaded by default.

## Automatic Docker build with GitHub Actions

This repository includes:

```text
.github/workflows/docker.yml
```

Every push to `main` builds the Docker image and publishes it to GitHub Container Registry (GHCR).

### First publish

1. Create a GitHub repository.
2. Upload the **contents of this folder** to the repository root. `Dockerfile` must be at the root.
3. Commit/push to the `main` branch.
4. Open **GitHub -> Actions -> Build and publish RunPod image**.
5. Wait for the workflow to finish successfully.

The resulting image is:

```text
ghcr.io/YOUR_GITHUB_USERNAME/runpod-comfy-h3-story:latest
```

A commit-specific tag is also published:

```text
ghcr.io/YOUR_GITHUB_USERNAME/runpod-comfy-h3-story:<full-git-commit-sha>
```

### GHCR visibility

For the simplest RunPod setup, make the generated GHCR package public after the first build. In GitHub, open your profile/organization **Packages**, open `runpod-comfy-h3-story`, then change the package visibility to **Public** in package settings.

If you keep it private, RunPod needs registry credentials with permission to read the package.

### RunPod image field

Use:

```text
ghcr.io/YOUR_GITHUB_USERNAME/runpod-comfy-h3-story:latest
```

For a fully reproducible deployment, use the commit SHA tag instead of `latest`.

### Updating

After changing the custom node, Dockerfile, startup scripts, or workflow:

```bash
git add .
git commit -m "update H3 workload"
git push
```

GitHub Actions will build and publish a new image automatically. H3 model weights are still stored on `/workspace`, not in the Docker image.
