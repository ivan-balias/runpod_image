FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG COMFYUI_REF=master

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/workspace/.cache/huggingface \
    COMFYUI_DIR=/opt/ComfyUI \
    WORKSPACE=/workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl wget ca-certificates ffmpeg python3 python3-pip python3-venv libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# CUDA-enabled PyTorch. H3 support benefits from a recent PyTorch/ComfyUI stack.
RUN python3 -m pip install --upgrade pip setuptools wheel && \
    python3 -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

RUN git clone https://github.com/Comfy-Org/ComfyUI.git ${COMFYUI_DIR} && \
    cd ${COMFYUI_DIR} && \
    git checkout ${COMFYUI_REF} && \
    python3 -m pip install -r requirements.txt

# Useful for video saving/preview in ComfyUI.
RUN git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git \
      ${COMFYUI_DIR}/custom_nodes/ComfyUI-VideoHelperSuite && \
    if [ -f ${COMFYUI_DIR}/custom_nodes/ComfyUI-VideoHelperSuite/requirements.txt ]; then \
      python3 -m pip install -r ${COMFYUI_DIR}/custom_nodes/ComfyUI-VideoHelperSuite/requirements.txt; \
    fi

# HF CLI for resumable model downloads to the persistent volume.
RUN python3 -m pip install "huggingface_hub[cli]>=0.30"

# Our custom scene-loop node.
COPY custom_nodes/story_scene_loop ${COMFYUI_DIR}/custom_nodes/story_scene_loop

COPY scripts /opt/story-scripts
COPY workflows /opt/story-workflows
COPY startup.sh /startup.sh
RUN chmod +x /startup.sh /opt/story-scripts/*.sh

EXPOSE 8188
CMD ["/startup.sh"]
