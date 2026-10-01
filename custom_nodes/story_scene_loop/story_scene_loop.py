import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import torch
from PIL import Image
import folder_paths


def _safe_name(value: str) -> str:
    value = (value or "project").strip()
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return value[:120] or "project"


def _save_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def _load_json(path: Path, default=None):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _tensor_to_pil(image: torch.Tensor) -> Image.Image:
    if image.ndim == 4:
        image = image[0]
    arr = image.detach().cpu().clamp(0, 1).numpy()
    arr = (arr * 255.0).round().astype(np.uint8)
    if arr.shape[-1] == 4:
        return Image.fromarray(arr, "RGBA")
    return Image.fromarray(arr[..., :3], "RGB")


def _pil_to_tensor(image: Image.Image) -> torch.Tensor:
    image = image.convert("RGB")
    arr = np.asarray(image).astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None, ...]


def _save_tensor(image: torch.Tensor, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    _tensor_to_pil(image).save(path)


def _load_tensor(path: Path) -> torch.Tensor:
    return _pil_to_tensor(Image.open(path))


def _resolve_video_path(raw_path: str) -> Path:
    p = Path(raw_path).expanduser()
    if p.is_absolute() and p.exists():
        return p
    candidates = [
        Path(folder_paths.get_output_directory()) / p,
        Path(folder_paths.get_temp_directory()) / p,
        Path(folder_paths.get_input_directory()) / p,
        p,
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()
    raise FileNotFoundError(f"Video file not found: {raw_path}")


def _extract_last_frame_ffmpeg(video_path: Path, out_png: Path):
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video_path), "-map", "0:v:0", "-vf", "reverse",
        "-frames:v", "1", str(out_png),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as e:
        raise RuntimeError("ffmpeg is not installed or not in PATH") from e
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(f"ffmpeg failed extracting last frame:\n{err}") from e
    if not out_png.exists():
        raise RuntimeError(f"Last frame was not created: {out_png}")


def _parse_master_prompt(master_prompt: str, scene_seconds: int, target_seconds: int):
    text = (master_prompt or "").strip()
    if not text:
        raise ValueError("master_prompt is empty")

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and isinstance(parsed.get("scenes"), list):
            result = []
            for i, item in enumerate(parsed["scenes"], 1):
                if isinstance(item, str):
                    prompt = item.strip()
                    duration = scene_seconds
                else:
                    prompt = str(item.get("prompt", "")).strip()
                    duration = int(item.get("duration", scene_seconds))
                if prompt:
                    result.append({"index": i, "name": f"scene_{i:03d}", "prompt": prompt, "duration": max(1, duration)})
            if result:
                return result
    except Exception:
        pass

    pattern = re.compile(
        r"(?:^|\n)\s*Scene\s*(\d+)\s*[:\-]\s*(.*?)(?=(?:\n\s*Scene\s*\d+\s*[:\-])|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    found = pattern.findall(text)
    if found:
        result = []
        for i, (_, body) in enumerate(found, 1):
            body = body.strip()
            if body:
                result.append({"index": i, "name": f"scene_{i:03d}", "prompt": body, "duration": scene_seconds})
        if result:
            return result

    if "---" in text:
        blocks = [b.strip() for b in text.split("---") if b.strip()]
        if blocks:
            return [{"index": i, "name": f"scene_{i:03d}", "prompt": body, "duration": scene_seconds} for i, body in enumerate(blocks, 1)]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) > 1:
        return [{"index": i, "name": f"scene_{i:03d}", "prompt": body, "duration": scene_seconds} for i, body in enumerate(paragraphs, 1)]

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    desired_count = max(1, int(round(target_seconds / max(1, scene_seconds))))
    if len(sentences) <= desired_count:
        chunks = sentences or [text]
    else:
        chunk_size = max(1, int(math.ceil(len(sentences) / desired_count)))
        chunks = [" ".join(sentences[i:i + chunk_size]) for i in range(0, len(sentences), chunk_size)]
    return [{"index": i, "name": f"scene_{i:03d}", "prompt": body, "duration": scene_seconds} for i, body in enumerate(chunks, 1)]


class StorySceneLoop:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "init_image": ("IMAGE",),
                "master_prompt": ("STRING", {"multiline": True, "default": "Scene 1: Milo walks happily through a sunny park holding a red balloon.\nScene 2: A sudden gust of wind pulls the balloon away and Milo looks shocked.\nScene 3: The balloon gets stuck high in a tree and Milo runs underneath it."}),
                "project_id": ("STRING", {"default": "milo_001"}),
                "mode": (["RESET", "CURRENT", "ADVANCE", "REGENERATE_ONE", "REGENERATE_FROM"],),
                "target_seconds": ("INT", {"default": 30, "min": 1, "max": 3600}),
                "scene_seconds": ("INT", {"default": 5, "min": 1, "max": 30}),
                "scene_number": ("INT", {"default": 1, "min": 1, "max": 9999}),
            },
            "optional": {
                "generated_video_path": ("STRING", {"default": "", "multiline": False}),
                "generated_frames": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "INT", "INT", "STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("scene_image", "scene_prompt", "filename_prefix", "scene_number", "total_scenes", "status", "project_dir", "finished")
    FUNCTION = "execute"
    CATEGORY = "Story Video"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def _paths(self, project_id: str):
        root = Path(folder_paths.get_output_directory()) / "story_scene_loop" / _safe_name(project_id)
        root.mkdir(parents=True, exist_ok=True)
        return {"root": root, "state": root / "state.json", "scenes": root / "scenes.json", "initial": root / "initial.png"}

    def _initialize(self, init_image, master_prompt, target_seconds, scene_seconds, paths):
        scenes = _parse_master_prompt(master_prompt, scene_seconds, target_seconds)
        _save_tensor(init_image, paths["initial"])
        _save_json(paths["scenes"], {"scenes": scenes})
        state = {"version": 1, "current_scene": 1, "total_scenes": len(scenes), "finished": False, "outputs": {}}
        _save_json(paths["state"], state)
        return state, scenes

    def _load_or_initialize(self, init_image, master_prompt, target_seconds, scene_seconds, paths):
        state = _load_json(paths["state"])
        data = _load_json(paths["scenes"])
        if not state or not data or not data.get("scenes"):
            return self._initialize(init_image, master_prompt, target_seconds, scene_seconds, paths)
        return state, data["scenes"]

    def _input_image_for_scene(self, state, paths, scene_number: int):
        if scene_number == 1:
            return _load_tensor(paths["initial"])
        previous = state["outputs"].get(str(scene_number - 1))
        if not previous:
            raise RuntimeError(f"Scene {scene_number} needs scene {scene_number - 1}, but the previous scene has no registered output")
        last_frame = Path(previous["last_frame"])
        if not last_frame.exists():
            raise RuntimeError(f"Missing last frame of scene {scene_number - 1}: {last_frame}")
        return _load_tensor(last_frame)

    def _register_result(self, state, paths, scene_number, generated_video_path="", generated_frames=None):
        scene_name = f"scene_{scene_number:03d}"
        last_frame_path = paths["root"] / f"{scene_name}_last.png"
        stored_video = None

        if generated_frames is not None:
            if not isinstance(generated_frames, torch.Tensor) or generated_frames.ndim != 4:
                raise RuntimeError("generated_frames must be a Comfy IMAGE batch [B,H,W,C]")
            _save_tensor(generated_frames[-1:].clone(), last_frame_path)
        elif (generated_video_path or "").strip():
            src = _resolve_video_path(generated_video_path.strip())
            ext = src.suffix if src.suffix else ".mp4"
            dst = paths["root"] / f"{scene_name}{ext}"
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
            _extract_last_frame_ffmpeg(dst, last_frame_path)
            stored_video = str(dst)
        else:
            raise RuntimeError("ADVANCE requires generated_frames or generated_video_path")

        state["outputs"][str(scene_number)] = {"video": stored_video, "last_frame": str(last_frame_path)}

    def _remove_from(self, state, paths, first_scene: int):
        for key in list(state["outputs"].keys()):
            if int(key) < first_scene:
                continue
            item = state["outputs"].pop(key)
            for value in item.values():
                if not value:
                    continue
                p = Path(value)
                try:
                    if p.exists() and paths["root"] in p.resolve().parents:
                        p.unlink()
                except Exception:
                    pass

    def _result(self, state, scenes, paths, scene_number):
        total = len(scenes)
        if scene_number > total:
            state["finished"] = True
            state["current_scene"] = total + 1
            _save_json(paths["state"], state)
            if total > 0 and str(total) in state["outputs"]:
                image = _load_tensor(Path(state["outputs"][str(total)]["last_frame"]))
            else:
                image = _load_tensor(paths["initial"])
            status = f"Finished · {len(state['outputs'])}/{total} scenes generated"
            return (image, "", "finished", total, total, status, str(paths["root"]), True)

        scene = scenes[scene_number - 1]
        image = self._input_image_for_scene(state, paths, scene_number)
        state["current_scene"] = scene_number
        state["finished"] = False
        _save_json(paths["state"], state)
        done = len(state["outputs"])
        status = f"Scene {scene_number}/{total} · generated {done}/{total}"
        return (image, scene["prompt"], scene["name"], scene_number, total, status, str(paths["root"]), False)

    def execute(self, init_image, master_prompt, project_id, mode, target_seconds, scene_seconds, scene_number, generated_video_path="", generated_frames=None):
        paths = self._paths(project_id)

        if mode == "RESET":
            for p in paths["root"].glob("*"):
                if p.is_file():
                    try:
                        p.unlink()
                    except Exception:
                        pass
            state, scenes = self._initialize(init_image, master_prompt, target_seconds, scene_seconds, paths)
            return self._result(state, scenes, paths, 1)

        state, scenes = self._load_or_initialize(init_image, master_prompt, target_seconds, scene_seconds, paths)

        if mode == "CURRENT":
            return self._result(state, scenes, paths, int(state.get("current_scene", 1)))

        if mode == "ADVANCE":
            current = int(state.get("current_scene", 1))
            self._register_result(state, paths, current, generated_video_path, generated_frames)
            state["current_scene"] = current + 1
            _save_json(paths["state"], state)
            return self._result(state, scenes, paths, current + 1)

        if mode == "REGENERATE_ONE":
            n = max(1, min(int(scene_number), len(scenes)))
            if generated_frames is not None or (generated_video_path or "").strip():
                self._register_result(state, paths, n, generated_video_path, generated_frames)
                _save_json(paths["state"], state)
            return self._result(state, scenes, paths, n)

        if mode == "REGENERATE_FROM":
            n = max(1, min(int(scene_number), len(scenes)))
            self._remove_from(state, paths, n)
            state["current_scene"] = n
            state["finished"] = False
            _save_json(paths["state"], state)
            return self._result(state, scenes, paths, n)

        raise RuntimeError(f"Unknown mode: {mode}")


NODE_CLASS_MAPPINGS = {"StorySceneLoop": StorySceneLoop}
NODE_DISPLAY_NAME_MAPPINGS = {"StorySceneLoop": "Story Scene Loop"}
