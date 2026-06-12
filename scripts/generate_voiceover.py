"""
scripts/generate_voiceover.py
─────────────────────────────────────────────────────────────
Generates a single full voiceover MP3 from a config JSON using
Microsoft Edge TTS (free, no API key required via edge-tts).

The script reads a "voiceover" field per scene (the narration line
for that scene). If a scene has no "voiceover" field, it falls back
to a flattened version of the scene's "data" text fields.

Output: assets/audio/full_voiceover.mp3
Also prints total audio duration — use this to sanity-check against
the sum of scene durations in your config.

Usage:
  python scripts/generate_voiceover.py \
    --config configs/wc2026_ep01.json \
    --output assets/audio/full_voiceover.mp3 \
    --voice en-US-GuyNeural
"""

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

try:
    import edge_tts
except ImportError:
    print("Installing edge-tts...")
    subprocess.run([sys.executable, "-m", "pip", "install", "edge-tts", "-q"])
    import edge_tts


# ─────────────────────────────────────────────
# TEXT EXTRACTION
# ─────────────────────────────────────────────
def scene_narration(scene: dict) -> str:
    """Get the narration line for a scene: explicit 'voiceover' field
    takes priority, otherwise flatten key text fields from 'data'."""
    if "voiceover" in scene and scene["voiceover"].strip():
        return scene["voiceover"].strip()

    d = scene.get("data", {})
    parts = []

    for key in ("line1", "line1_accent", "line2", "line2_accent",
                "headline", "headline_accent", "body", "quote",
                "stat_context", "name"):
        val = d.get(key)
        if val:
            parts.append(str(val))

    return " ".join(parts).strip()


# ─────────────────────────────────────────────
# TTS
# ─────────────────────────────────────────────
async def synthesize(text: str, voice: str, dest: Path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(dest))


def run_ffmpeg(args, desc=""):
    cmd = ["ffmpeg", "-y"] + args
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"\n  ❌ FFmpeg error ({desc}):")
        print(result.stderr.decode()[-1200:])
        return False
    return True


def get_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        return float(result.stdout.decode().strip())
    except ValueError:
        return 0.0


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
async def main_async(args):
    config_path = Path(args.config)
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    scenes = config["scenes"]
    work_dir = Path("assets/audio/_scenes")
    work_dir.mkdir(parents=True, exist_ok=True)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"🎙️  Generating voiceover for {len(scenes)} scenes (voice: {args.voice})\n")

    scene_files = []
    for scene in scenes:
        sid = scene["id"]
        text = scene_narration(scene)
        if not text:
            print(f"  ⚠️  {sid}: no narration text found, skipping")
            continue

        dest = work_dir / f"{sid}.mp3"
        print(f"  🔊 {sid}: \"{text[:60]}{'...' if len(text) > 60 else ''}\"")
        await synthesize(text, args.voice, dest)
        dur = get_duration(dest)
        target = scene["duration"]
        flag = "⚠️  longer than scene!" if dur > target else ""
        print(f"     ↳ {dur:.1f}s (scene budget: {target}s) {flag}")
        scene_files.append(dest)

    if not scene_files:
        print("\n❌ No narration generated.")
        sys.exit(1)

    concat_list = work_dir / "concat_list.txt"
    with open(concat_list, "w") as f:
        for p in scene_files:
            f.write(f"file '{p.resolve().as_posix()}'\n")

    print(f"\n🎬 Concatenating {len(scene_files)} clips → {out_path}")
    ok = run_ffmpeg([
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:a", "libmp3lame", "-q:a", "2",
        str(out_path)
    ], desc="concat voiceover")

    if not ok:
        sys.exit(1)

    total_dur = get_duration(out_path)
    config_total = sum(s["duration"] for s in scenes)
    print(f"\n✅ {out_path} — {total_dur:.1f}s")
    print(f"   Config scene total: {config_total:.0f}s")
    if abs(total_dur - config_total) > 5:
        print(f"   ⚠️  Difference of {abs(total_dur - config_total):.1f}s — "
              f"consider adjusting scene durations in the config to match voiceover pacing.")


def main():
    parser = argparse.ArgumentParser(description="Generate voiceover audio from config JSON")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", default="assets/audio/full_voiceover.mp3")
    parser.add_argument("--voice", default="en-US-GuyNeural",
                         help="Edge TTS voice name (e.g. en-US-GuyNeural, en-GB-RyanNeural)")
    args = parser.parse_args()

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
