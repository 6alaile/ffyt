"""
Football Channel — Unified Pipeline
-------------------------------------
Usage:
  python pipeline.py --config configs/video_03.json

Steps:
  1. Generate voiceover (Edge TTS — free, unlimited)
  2. Download clips from Pixabay
  3. Process clips + text overlays
  4. Stitch final video
  5. Upload to YouTube
"""

import argparse
import json
import sys
from pathlib import Path

from scripts.voiceover import generate_voiceover
from scripts.video import produce_video
from scripts.upload import upload_to_youtube


def load_config(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"❌ Config file not found: {path}")
        sys.exit(1)
    with open(p) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Football Channel Pipeline")
    parser.add_argument("--config", required=True, help="Path to video config JSON")
    parser.add_argument("--skip-upload", action="store_true", help="Skip YouTube upload step")
    args = parser.parse_args()

    config = load_config(args.config)
    video_id = config["video_id"]

    print("=" * 60)
    print(f"  PIPELINE — {video_id}")
    print(f"  {config['title']}")
    print("=" * 60)

    # Step 1 — Voiceover
    print("\n🎙️  STEP 1: Generating voiceover...")
    audio_path = generate_voiceover(config)

    # Step 2 + 3 + 4 — Video production
    print("\n🎬 STEP 2–4: Producing video...")
    video_path = produce_video(config, audio_path)

    # Step 5 — Upload
    if not args.skip_upload:
        print("\n📤 STEP 5: Uploading to YouTube...")
        upload_to_youtube(config, video_path)
    else:
        print(f"\n⏭️  Skipping upload. Final video: {video_path}")

    print("\n🏆 PIPELINE COMPLETE\n")


if __name__ == "__main__":
    main()
