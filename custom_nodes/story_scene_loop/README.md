# Story Scene Loop for ComfyUI

Copy this folder to `ComfyUI/custom_nodes/story_scene_loop/` and restart ComfyUI.

Node path: `Story Video -> Story Scene Loop`.

## Flow
1. `RESET` -> outputs scene 1 image + prompt.
2. Generate video.
3. Feed the generated frame batch into `generated_frames` (preferred) or provide the saved file path in `generated_video_path`.
4. `ADVANCE` -> stores scene N last frame and outputs scene N+1 image + prompt.
5. Repeat.

State is stored at `ComfyUI/output/story_scene_loop/<project_id>/`.

Master prompt can use `Scene 1: ...`, `Scene 2: ...`, `---` separators, or JSON with a `scenes` array.

If using `generated_video_path`, ffmpeg must be installed. If using `generated_frames`, ffmpeg is not needed to extract the final frame.
