"""
scripts/video.py
Downloads clips from Pixabay, applies text overlays, stitches final video,
then merges the voiceover audio.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from tqdm import tqdm

PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720


# ─────────────────────────────────────────────
# PIXABAY
# ─────────────────────────────────────────────
def search_pixabay_video(query: str, min_duration: int = 10) -> str | None:
    """Search Pixabay for a landscape video clip. Returns direct video URL or None."""
    if not PIXABAY_API_KEY:
        raise RuntimeError("PIXABAY_API_KEY not set. Add it to GitHub Secrets.")

    params = {
        "key": PIXABAY_API_KEY,
        "q": query,
        "video_type": "film",
        "orientation": "horizontal",
        "per_page": 10,
        "safesearch": "true",
    }

    try:
        resp = requests.get(
            "https://pixabay.com/api/videos/",
            params=params,
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  Pixabay search failed: {e}")
        return None

    for hit in data.get("hits", []):
        if hit.get("duration", 0) < min_duration:
            continue
        videos = hit.get("videos", {})
        # Prefer large (1920), fall back to medium (1280), then small
        for quality in ["large", "medium", "small"]:
            v = videos.get(quality, {})
            if v.get("url"):
                return v["url"]

    return None


def download_file(url: str, dest: Path) -> bool:
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True,
            desc=f"  {dest.name}", leave=False
        ) as bar:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))
        return True
    except Exception as e:
        print(f"  Download failed: {e}")
        return False


# ─────────────────────────────────────────────
# PILLOW TEXT OVERLAY
# ─────────────────────────────────────────────
def ensure_pillow():
    try:
        from PIL import Image
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "pillow", "-q"])


def make_text_overlay_png(text: str, font_size: int, dest: Path,
                           is_fallback: bool = False) -> bool:
    from PIL import Image, ImageDraw, ImageFont

    width, height = VIDEO_WIDTH, VIDEO_HEIGHT

    if is_fallback:
        img = Image.new("RGB", (width, height), color=(10, 10, 10))
    else:
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    draw = ImageDraw.Draw(img)

    # Try system fonts (Linux/GitHub Actions + Windows)
    font = None
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",   # Ubuntu (GitHub Actions)
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for fp in font_candidates:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()

    lines = text.split("\n")
    line_height = font_size + 12
    total_h = line_height * len(lines)

    y_start = int(height * 0.78) - total_h // 2 if not is_fallback else (height - total_h) // 2
    color = (255, 255, 255) if is_fallback else (255, 215, 0)

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2
        y = y_start + i * line_height

        if not is_fallback:
            pad = 14
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            box_draw = ImageDraw.Draw(overlay)
            box_draw.rectangle(
                [x - pad, y - pad, x + text_w + pad, y + font_size + pad],
                fill=(0, 0, 0, 140)
            )
            img = Image.alpha_composite(img, overlay)
            draw = ImageDraw.Draw(img)

        draw.text((x, y), line, font=font, fill=color)

    img.save(str(dest))
    return True


# ─────────────────────────────────────────────
# FFMPEG HELPERS
# ─────────────────────────────────────────────
def run_ffmpeg(args: list, desc: str = "") -> bool:
    result = subprocess.run(
        ["ffmpeg", "-y"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    if result.returncode != 0:
        print(f"\n  ❌ FFmpeg error ({desc}):")
        print(result.stderr.decode()[-1500:])
        return False
    return True


def make_fallback_clip(scene: dict, clips_dir: Path, dest: Path) -> bool:
    png = clips_dir / f"{scene['id']}_card.png"
    make_text_overlay_png(scene["text"], scene.get("text_size", 48), png, is_fallback=True)
    return run_ffmpeg([
        "-loop", "1", "-i", str(png),
        "-c:v", "libx264", "-t", str(scene["duration"]),
        "-pix_fmt", "yuv420p", "-r", "30",
        str(dest)
    ], desc=f"fallback {scene['id']}")


def process_clip(scene: dict, raw_path: Path | None, clips_dir: Path, dest: Path) -> bool:
    if raw_path is None or not raw_path.exists():
        return make_fallback_clip(scene, clips_dir, dest)

    duration = scene["duration"]

    scaled = clips_dir / f"{scene['id']}_scaled.mp4"
    ok = run_ffmpeg([
        "-i", str(raw_path),
        "-ss", "0", "-t", str(duration),
        "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}",
        "-af", "volume=0.0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-r", "30", "-c:a", "aac", "-ar", "44100",
        str(scaled)
    ], desc=f"scale {scene['id']}")
    if not ok:
        return False

    png = clips_dir / f"{scene['id']}_overlay.png"
    make_text_overlay_png(scene["text"], scene.get("text_size", 48), png, is_fallback=False)

    return run_ffmpeg([
        "-i", str(scaled),
        "-i", str(png),
        "-filter_complex", "[0:v][1:v]overlay=0:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        str(dest)
    ], desc=f"overlay {scene['id']}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def produce_video(config: dict, audio_path: Path) -> Path:
    """Download, process, stitch, merge audio. Returns final video path."""
    ensure_pillow()

    video_id = config["video_id"]
    scenes = config["scenes"]

    work_dir = Path(f"output/{video_id}")
    clips_dir = work_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Download clips
    print("\n  📥 Downloading clips from Pixabay...")
    raw_paths = {}
    for scene in scenes:
        sid = scene["id"]
        dest = clips_dir / f"{sid}_raw.mp4"
        if dest.exists():
            print(f"  ✓ {sid} (cached)")
            raw_paths[sid] = dest
            continue
        print(f"  🔍 {sid}: {scene['query']}")
        url = search_pixabay_video(scene["query"], min_duration=scene["duration"])
        if not url:
            print(f"  ⚠️  No clip found for {sid} — using fallback card")
            raw_paths[sid] = None
        else:
            ok = download_file(url, dest)
            raw_paths[sid] = dest if ok else None
        time.sleep(0.4)

    # Step 2: Process clips
    print("\n  ✂️  Processing clips...")
    processed = []
    for scene in scenes:
        sid = scene["id"]
        dest = clips_dir / f"{sid}_processed.mp4"
        if dest.exists():
            print(f"  ✓ {sid} (cached)")
            processed.append(dest)
            continue
        print(f"  ⚙️  {sid}...")
        ok = process_clip(scene, raw_paths.get(sid), clips_dir, dest)
        if ok:
            processed.append(dest)
            print(f"  ✓ {sid}")
        else:
            print(f"  ❌ {sid} failed")

    if not processed:
        raise RuntimeError("No clips processed.")

    # Step 3: Stitch
    print("\n  🎬 Stitching clips...")
    concat_list = work_dir / "concat_list.txt"
    silent_video = work_dir / f"{video_id}_silent.mp4"

    with open(concat_list, "w") as f:
        for p in processed:
            f.write(f"file '{p.resolve()}'\n")

    ok = run_ffmpeg([
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-movflags", "+faststart",
        str(silent_video)
    ], desc="stitch")

    if not ok:
        raise RuntimeError("Stitch failed.")

    # Step 4: Merge voiceover
    print(f"\n  🔊 Merging voiceover...")
    final_video = work_dir / f"{video_id}_FINAL.mp4"

    ok = run_ffmpeg([
        "-i", str(silent_video),
        "-i", str(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        "-movflags", "+faststart",
        str(final_video)
    ], desc="merge audio")

    if not ok:
        raise RuntimeError("Audio merge failed.")

    size_mb = final_video.stat().st_size / 1_000_000
    print(f"  ✅ Final video: {final_video} ({size_mb:.1f} MB)")
    return final_video
