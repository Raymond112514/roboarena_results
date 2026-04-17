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
    ("dropout20000", "Dropout 20000"),
    ("no_dropout20000", "No dropout 20000"),
    ("dropout40000", "Dropout 40000"),
    ("no_dropout40000", "No dropout 40000"),
]


@st.cache_data
def list_trajectories() -> list[str]:
    first = BASE / DATASETS[0][0]
    if not first.is_dir():
        return []
    return sorted(p.name for p in first.iterdir() if p.is_dir())


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


def _synced_videos_html(items: list[tuple[str, str, Path]]) -> str:
    """Four-column grid, one shared scrubber (HTML5 videos; same length assumed)."""
    cols_html: list[str] = []
    for label, folder, vid_path in items:
        title = html_stdlib.escape(f"{label} — {folder}")
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
  .title {{ font-weight: 600; margin-bottom: 6px; line-height: 1.3; word-break: break-word; }}
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
    st.title("Trajectory visualization")
    st.caption("One trajectory × four runs: short video and attention heatmap per condition.")

    trajectories = list_trajectories()
    if not trajectories:
        st.error(f"No trajectory folders found under `{DATASETS[0][0]}`.")
        st.stop()

    if "selected_traj" not in st.session_state:
        st.session_state.selected_traj = trajectories[0]

    def pick_random() -> None:
        st.session_state.selected_traj = random.choice(trajectories)

    row1, row2 = st.columns([4, 1])
    with row1:
        idx = (
            trajectories.index(st.session_state.selected_traj)
            if st.session_state.selected_traj in trajectories
            else 0
        )
        choice = st.selectbox("Trajectory", trajectories, index=idx)
        st.session_state.selected_traj = choice
    with row2:
        st.button("Random trajectory", on_click=pick_random, type="primary")

    st.divider()
    st.subheader(choice)

    paths = trajectory_paths(choice)
    video_inputs = [(label, folder, vid) for folder, label, vid, hm in paths]
    # Height ~ content (grid + controls) to avoid a tall empty band under the scrubber.
    html_component(_synced_videos_html(video_inputs), height=400, scrolling=False)

    cols = st.columns(4)
    for col, (folder, label, vid, hm) in zip(cols, paths):
        with col:
            if hm.is_file():
                st.image(str(hm), use_container_width=True, caption=f"{label} — `{folder}`")
            else:
                st.warning(f"Missing: `{hm.name}`")


if __name__ == "__main__":
    main()
