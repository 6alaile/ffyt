"""
scripts/fetch_clips.py
─────────────────────────────────────────────────────────────
Downloads and processes a stock video clip for each scene in a
config JSON using the Pixabay API. Falls back to Pexels if
PIXABAY_API_KEY is unset but PEXELS_API_KEY is set.

Output: assets/clips/{scene_id}_processed.mp4
  - Scaled and cropped to the target resolution (1920x1080 or 1080x1920)
  - Muted (audio comes from the voiceover track)
  - Trimmed to scene duration

Usage:
  python scripts/fetch_clips.py \
    --config configs/wc2026_ep01.json \
    --format landscape \
    --outdir assets/clips
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from tqdm import tqdm


FORMATS = {
    "landscape": {"width": 1920, "height": 1080, "orientation": "horizontal"},
    "portrait":  {"width": 1080, "height": 1920, "orientation": "vertical"},
}

PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")


# ─────────────────────────────────────────────
# PIXABAY SEARCH
# ─────────────────────────────────────────────
def search_pixabay_video(query: str, min_duration: int = 5):
    if not PIXABAY_API_KEY:
        return None
    params = {
        "key": PIXABAY_API_KEY,
        "q": query,
        "per_page": 20,
    }
    try:
        resp = requests.get("https://pixabay.com/api/videos/", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  ⚠️  Pixabay search failed: {e}")
        return None

    for hit in data.get("hits", []):
        if hit.get("duration", 0) < min_duration:
            continue
        videos = hit.get("videos", {})
        for size in ("large", "medium", "small"):
            v = videos.get(size)
            if v and v.get("url"):
                return v["url"]
    return None


# ─────────────────────────────────────────────
# PEXELS FALLBACK
# ─────────────────────────────────────────────
def search_pexels_video(query: str, min_duration: int = 5):
    if not PEXELS_API_KEY:
        return None
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 10, "orientation": "landscape"}
    try:
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers, params=params, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  ⚠️  Pexels search failed: {e}")
        return None

    for video in data.get("videos", []):
        if video.get("duration", 0) < min_duration:
            continue
        files = video.get("video_files", [])
        hd = [f for f in files if f.get("width", 0) >= 1280]
        if not hd:
            hd = files
        hd.sort(key=lambda f: f.get("width", 0), reverse=True)
        for f in hd:
            if f.get("width", 9999) <= 1920:
                return f.get("link")
    return None


def search_clip(query: str, min_duration: int = 5):
    url = search_pixabay_video(query, min_duration)
    if url:
        return url, "pixabay"
    url = search_pexels_video(query, min_duration)
    if url:
        return url, "pexels"
    return None, None


# ─────────────────────────────────────────────
# DOWNLOAD
# ─────────────────────────────────────────────
def download_file(url: str, dest: Path) -> bool:
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=f"  {dest.name}", leave=False
        ) as bar:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))
        return True
    except Exception as e:
        print(f"  ⚠️  Download failed: {e}")
        return False


# ─────────────────────────────────────────────
# FFMPEG PROCESSING
# ─────────────────────────────────────────────
def run_ffmpeg(args, desc=""):
	# Force Constant Frame Rate (r=30), force resolution, and drop existing audio (-an)
        cmd = [
            "ffmpeg", "-y", "-i", str(raw_path),
            "-ss", "0", "-t", str(duration),
            "-r", "30",  # Matches Hyperframes deterministic timeline stepping
            "-an",  # Strips clip audio so Chrome doesn't clash with full_voiceover.mp3
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
            str(dest)
        ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"\n  ❌ FFmpeg error ({desc}):")
        print(result.stderr.decode()[-1200:])
        return False
    return True


def make_fallback_clip(scene: dict, dest: Path, w: int, h: int):
    """Solid dark card if no clip is found — HyperFrames text still renders on top."""
    return run_ffmpeg([
        "-f", "lavfi",
        "-i", f"color=c=0x0a0a0a:s={w}x{h}:d={scene['duration']}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        str(dest)
    ], desc=f"fallback {scene['id']}")


def process_clip(scene: dict, raw_path, dest: Path, w: int, h: int):
    if raw_path is None or not Path(raw_path).exists():
        return make_fallback_clip(scene, dest, w, h)

    duration = scene["duration"]
    return run_ffmpeg([
        "-stream_loop", "-1",
        "-i", str(raw_path),
        "-t", str(duration),
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
        "-an",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-r", "30",
        str(dest)
    ], desc=f"process {scene['id']}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Fetch and process stock clips for a video config")
    parser.add_argument("--config", required=True)
    parser.add_argument("--format", choices=["landscape", "portrait"], default="landscape")
    parser.add_argument("--outdir", default="assets/clips")
    args = parser.parse_args()

    if not PIXABAY_API_KEY and not PEXELS_API_KEY:
        print("❌ Neither PIXABAY_API_KEY nor PEXELS_API_KEY is set.")
        sys.exit(1)

    config_path = Path(args.config)
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    fmt = FORMATS[args.format]
    w, h = fmt["width"], fmt["height"]

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    raw_dir = outdir / "_raw"
    raw_dir.mkdir(exist_ok=True)

    scenes = config["scenes"]
    print(f"📥 Fetching {len(scenes)} clips ({args.format}, {w}x{h})\n")

    for scene in scenes:
        sid = scene["id"]
        dest = outdir / f"{sid}_processed.mp4"
        if dest.exists():
            print(f"  ✓ {sid} already processed, skipping")
            continue

        query = scene.get("clip_query", "football")
        if "football" not in query.lower():
            query = f"{query} football"
        print(f"  🔍 {sid}: \"{query}\"")

        url, source = search_clip(query, min_duration=3)
        raw_path = None
        if url:
            raw_path = raw_dir / f"{sid}_raw.mp4"
            ok = download_file(url, raw_path)
            if ok:
                print(f"     ↳ downloaded from {source}")
            else:
                raw_path = None
        else:
            print(f"     ↳ no clip found, using fallback card")

        ok = process_clip(scene, raw_path, dest, w, h)
        if ok:
            print(f"  ✓ {sid} ready")
        else:
            print(f"  ❌ {sid} failed")

        time.sleep(0.5)

    print(f"\n✅ Clips in {outdir}/")


if __name__ == "__main__":
    main()