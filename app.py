"""
Visualize one trajectory across four model runs: video + heatmap per condition.
"""
from __future__ import annotations

import base64
import html as html_stdlib
import random
from pathlib import Path

import streamlit as st
from streamlit.components.v1 import html as html_component

BASE = Path(__file__).resolve().parent

DATASETS: list[tuple[str, str]] = [
    ("droid_p0.5_step20000", "DROID only"),
    ("roboarena_p0.0_step20000", "Roboarena p=0.0, step 20000"),
    ("roboarena_p0.2_step20000", "Roboarena p=0.2, step 20000"),
    ("roboarena_p0.5_step20000", "Roboarena p=0.5, step 20000"),
    ("droid_p0.5_step40000", "DROID only"),
    ("roboarena_p0.0_step40000", "Roboarena p=0.0, step 40000"),
    ("roboarena_p0.2_step40000", "Roboarena p=0.2, step 40000"),
    ("roboarena_p0.5_step40000", "Roboarena p=0.5, step 40000"),
]


@st.cache_data
def list_trajectories() -> list[str]:
    first = BASE / DATASETS[0][0]
    if not first.is_dir():
        return []
    return sorted(p.name for p in first.iterdir() if p.is_dir())


def trajectory_group(name: str) -> str | None:
    """Return 'train' or 'test' from leading task id, else None."""
    prefix = name.split("_", 1)[0]
    try:
        task_id = int(prefix)
    except ValueError:
        return None

    if 0 <= task_id <= 39:
        return "train"
    if 40 <= task_id <= 46:
        return "test"
    return None


def trajectory_paths(name: str) -> list[tuple[str, str, Path, Path]]:
    """Return (folder_key, label, video_path, heatmap_path) for each dataset."""
    out: list[tuple[str, str, Path, Path]] = []
    for folder, label in DATASETS:
        root = BASE / folder / name
        out.append((folder, label, root / "value_function.mp4", root / "heatmap.png"))
    return out


@st.cache_data(max_entries=128, show_spinner=False)
def _mp4_base64(path_str: str) -> str:
    return base64.b64encode(Path(path_str).read_bytes()).decode("ascii")


def _synced_videos_html(items: list[tuple[str, Path]]) -> str:
    """Four-column grid, one shared scrubber (HTML5 videos; same length assumed)."""
    cols_html: list[str] = []
    for label, vid_path in items:
        title = html_stdlib.escape(label)
        if vid_path.is_file():
            b64 = _mp4_base64(str(vid_path.resolve()))
            media = (
                f'<video class="synced" preload="auto" muted playsinline '
                f'src="data:video/mp4;base64,{b64}"></video>'
            )
        else:
            media = f'<div class="missing">Missing `{html_stdlib.escape(vid_path.name)}`</div>'
        cols_html.append(f'<div class="cell"><div class="title">{title}</div>{media}</div>')

    # fmt: off
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: system-ui, sans-serif; font-size: 13px; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; align-items: start; }}
  .title {{ font-weight: 400; margin-bottom: 6px; line-height: 1.3; word-break: break-word; color: #6b7280; font-size: 0.9rem; }}
  video.synced {{ width: 100%; max-height: 220px; background: #111; border-radius: 6px; }}
  .missing {{ padding: 24px 8px; text-align: center; color: #888; background: #f3f3f3; border-radius: 6px; min-height: 120px; }}
  .controls {{ margin-top: 6px; padding-top: 6px; border-top: 1px solid #ddd; }}
  .controls label {{ display: block; margin-bottom: 3px; color: #444; font-size: 12px; }}
  #scrub {{ width: 100%; margin: 0; }}
  .btns {{ margin-top: 4px; display: flex; gap: 6px; flex-wrap: wrap; }}
  button {{ padding: 4px 10px; cursor: pointer; font-size: 12px; }}
</style></head><body>
  <div class="grid">{"".join(cols_html)}</div>
  <div class="controls">
    <label for="scrub">Scrub (all videos)</label>
    <input type="range" id="scrub" min="0" max="1000" value="0" step="1" disabled />
    <div class="btns">
      <button type="button" id="play">Play</button>
      <button type="button" id="pause">Pause</button>
    </div>
  </div>
<script>
(function() {{
  const videos = Array.from(document.querySelectorAll("video.synced"));
  const scrub = document.getElementById("scrub");
  const playBtn = document.getElementById("play");
  const pauseBtn = document.getElementById("pause");
  let duration = 0;
  let scrubbing = false;

  function syncDuration() {{
    const d = Math.max(0, ...videos.map((v) => v.duration || 0));
    if (d && isFinite(d)) {{
      duration = d;
      scrub.disabled = false;
    }}
  }}
  videos.forEach((v) => v.addEventListener("loadedmetadata", syncDuration));

  scrub.addEventListener("input", () => {{
    const t = (parseFloat(scrub.value) / 1000) * duration;
    videos.forEach((v) => {{ try {{ v.currentTime = t; }} catch (e) {{}} }});
  }});

  scrub.addEventListener("mousedown", () => {{ scrubbing = true; }});
  scrub.addEventListener("mouseup", () => {{ scrubbing = false; }});
  scrub.addEventListener("touchstart", () => {{ scrubbing = true; }});
  scrub.addEventListener("touchend", () => {{ scrubbing = false; }});

  const leader = videos[0];
  if (leader) {{
    leader.addEventListener("timeupdate", () => {{
      if (scrubbing || !duration) return;
      scrub.value = String((leader.currentTime / duration) * 1000);
    }});
  }}

  playBtn.addEventListener("click", () => {{
    videos.forEach((v) => {{ v.play().catch(() => {{}}); }});
  }});
  pauseBtn.addEventListener("click", () => {{
    videos.forEach((v) => v.pause());
  }});
}})();
</script>
</body></html>"""
    # fmt: on


def main() -> None:
    st.set_page_config(page_title="Trajectory comparison", layout="wide")
    st.title("Bageljax Value Function Visualization")
    st.caption("April 20 Progress Update")

    trajectories = list_trajectories()
    if not trajectories:
        st.error(f"No trajectory folders found under `{DATASETS[0][0]}`.")
        st.stop()

    if "selected_traj" not in st.session_state:
        st.session_state.selected_traj = trajectories[0]

    train_trajectories = [t for t in trajectories if trajectory_group(t) == "train"]
    test_trajectories = [t for t in trajectories if trajectory_group(t) == "test"]

    def pick_random_train() -> None:
        if train_trajectories:
            st.session_state.selected_traj = random.choice(train_trajectories)

    def pick_random_test() -> None:
        if test_trajectories:
            st.session_state.selected_traj = random.choice(test_trajectories)

    st.markdown("Trajectory")
    row1, row2, row3 = st.columns([4, 1, 1])
    with row1:
        idx = (
            trajectories.index(st.session_state.selected_traj)
            if st.session_state.selected_traj in trajectories
            else 0
        )
        choice = st.selectbox(
            "Trajectory",
            trajectories,
            index=idx,
            label_visibility="collapsed",
        )
        st.session_state.selected_traj = choice
    with row2:
        st.button(
            "Random train trajectory",
            on_click=pick_random_train,
            type="primary",
            disabled=not train_trajectories,
        )
    with row3:
        st.button(
            "Random test trajectory",
            on_click=pick_random_test,
            disabled=not test_trajectories,
        )

    st.divider()
    with st.expander("Info"):
        st.write("id 0-39 is training set, id 40-46 is testing set")
    st.subheader(choice)

    paths = trajectory_paths(choice)
    video_inputs = [(label, vid) for folder, label, vid, hm in paths]
    # Two rows of videos + scrubber controls.
    num_rows = (len(video_inputs) + 3) // 4
    html_height = 220 * num_rows + 120
    html_component(_synced_videos_html(video_inputs), height=html_height, scrolling=False)

    # Heatmaps in the same 2x4 organization.
    for row_start in range(0, len(paths), 4):
        cols = st.columns(4)
        row_items = paths[row_start : row_start + 4]
        for col, (folder, label, vid, hm) in zip(cols, row_items):
            with col:
                if hm.is_file():
                    st.image(str(hm), use_container_width=True, caption=label)
                else:
                    st.warning(f"Missing: `{hm.name}`")


if __name__ == "__main__":
    main()
