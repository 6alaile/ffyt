"""
Football Channel — Unified Pipeline
────────────────────────────────────
Local-only pipeline for testing (GitHub Actions uses direct CLI steps).

Usage:
  python pipeline.py --config configs/wc2026_ep01.json

Note: Requires Node.js 22 and HyperFrames CLI installed globally:
  npm install -g hyperframes

Steps:
  1. Generate HTML composition
  2. Download clips from Pixabay
  3. Generate voiceover (Edge TTS — free, unlimited)
  4. Render video with HyperFrames
  5. Upload to YouTube
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from scripts.generate_html import main as generate_html
from scripts.fetch_clips import main as fetch_clips
from scripts.generate_voiceover import main as generate_voiceover
from scripts.upload import upload_video


def load_config(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"❌ Config file not found: {path}")
        sys.exit(1)
    with open(p) as f:
        return json.load(f)


def run_hyperframes_render(composition_html: str, output_video: str, format_name: str) -> bool:
    """Render HTML composition to video using HyperFrames CLI."""
    cmd = [
        "npx", "hyperframes", "render",
        "--input", composition_html,
        "--output", output_video,
        "--headless",
        "--fps", "30",
        "--workers", "4"
    ]
    
    print(f"🎬 Rendering video with HyperFrames → {output_video}...")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"❌ HyperFrames render failed")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Football Channel Pipeline (Local)")
    parser.add_argument("--config", required=True, help="Path to video config JSON")
    parser.add_argument("--format", choices=["landscape", "portrait"], default="landscape")
    parser.add_argument("--skip-upload", action="store_true", help="Skip YouTube upload step")
    args = parser.parse_args()

    config = load_config(args.config)
    video_id = config.get("video_id", "video_01")
    title = config.get("title", "Untitled")

    print("=" * 60)
    print(f"  PIPELINE — {video_id}")
    print(f"  {title}")
    print(f"  Format: {args.format}")
    print("=" * 60)

    # Step 1 — Generate HTML composition
    print("\n📝 STEP 1: Generating HTML composition...")
    composition_path = "composition.html"
    sys.argv = [
        "generate_html",
        "--config", args.config,
        "--format", args.format,
        "--output", composition_path
    ]
    try:
        generate_html()
    except SystemExit:
        pass  # generate_html calls sys.exit(0) on success

    # Step 2 — Fetch clips from Pixabay
    print("\n📥 STEP 2: Downloading clips from Pixabay...")
    sys.argv = [
        "fetch_clips",
        "--config", args.config,
        "--format", args.format,
        "--outdir", "assets/clips"
    ]
    try:
        fetch_clips()
    except SystemExit:
        pass

    # Step 3 — Generate voiceover
    print("\n🎙️  STEP 3: Generating voiceover...")
    sys.argv = [
        "generate_voiceover",
        "--config", args.config,
        "--output", "assets/audio/full_voiceover.mp3"
    ]
    try:
        generate_voiceover()
    except SystemExit:
        pass

    # Step 4 — Render video with HyperFrames
    print("\n🎬 STEP 4: Rendering video with HyperFrames...")
    output_video = "output_raw.mp4"
    ok = run_hyperframes_render(composition_path, output_video, args.format)
    if not ok:
        print("❌ Pipeline failed at render step")
        sys.exit(1)

    # Step 5 — Upload to YouTube
    if not args.skip_upload:
        print("\n📤 STEP 5: Uploading to YouTube...")
        video_path = Path(output_video)
        if not video_path.exists():
            print(f"❌ Video file not found: {video_path}")
            sys.exit(1)
        upload_video(video_path, config)
    else:
        print(f"\n⏭️  Skipping upload. Final video: {output_video}")

    print("\n🏆 PIPELINE COMPLETE\n")


if __name__ == "__main__":
    main()
