"""
scripts/voiceover.py
Generates per-scene MP3s and a combined full_voiceover.mp3
using Edge TTS (free, unlimited, no API key needed).

To swap to ElevenLabs later, replace generate_scene_audio() only.
"""

import asyncio
import subprocess
import time
from pathlib import Path

import edge_tts


# ─────────────────────────────────────────────
# VOICE OPTIONS (Edge TTS — all free)
# Best for sports narration:
#   en-US-GuyNeural       — deep, authoritative
#   en-US-ChristopherNeural — smooth, broadcast feel
#   en-GB-RyanNeural      — British, punchy
# ─────────────────────────────────────────────
DEFAULT_VOICE = "en-US-GuyNeural"


async def _synthesize(text: str, voice: str, output_path: Path):
    tts = edge_tts.Communicate(text, voice=voice)
    await tts.save(str(output_path))


def generate_scene_audio(text: str, output_path: Path, voice: str = DEFAULT_VOICE) -> bool:
    """Generate audio for a single scene. Swap this function to change TTS provider."""
    try:
        asyncio.run(_synthesize(text, voice, output_path))
        return True
    except Exception as e:
        print(f"  ❌ TTS error: {e}")
        return False


def combine_audio_files(scene_files: list, audio_dir: Path) -> Path | None:
    """Concatenate all scene mp3s into one full_voiceover.mp3 using ffmpeg."""
    concat_list = audio_dir / "audio_concat.txt"
    output = audio_dir / "full_voiceover.mp3"

    with open(concat_list, "w") as f:
        for p in scene_files:
            f.write(f"file '{Path(p).resolve()}'\n")

    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c:a", "libmp3lame", "-q:a", "2",
            str(output)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if result.returncode != 0:
        print("  ❌ FFmpeg audio concat failed:")
        print(result.stderr.decode()[-1000:])
        return None

    return output


def generate_voiceover(config: dict) -> Path:
    """Main entry point. Returns path to full_voiceover.mp3."""
    video_id = config["video_id"]
    scenes = config["scenes"]
    voice = config.get("voice", DEFAULT_VOICE)

    audio_dir = Path(f"output/{video_id}/audio")
    audio_dir.mkdir(parents=True, exist_ok=True)

    total_chars = sum(len(s["text"]) for s in scenes)
    print(f"  Voice: {voice}")
    print(f"  Scenes: {len(scenes)} | Characters: {total_chars}")

    scene_files = []
    for i, scene in enumerate(scenes, 1):
        sid = scene["id"]
        dest = audio_dir / f"{sid}.mp3"

        if dest.exists():
            print(f"  ✓ [{i}/{len(scenes)}] {sid} (cached)")
            scene_files.append(dest)
            continue

        print(f"  🎙️  [{i}/{len(scenes)}] {sid}...")
        ok = generate_scene_audio(scene["text"], dest, voice)

        if ok:
            size_kb = dest.stat().st_size // 1024
            print(f"  ✓ {sid} → {size_kb}KB")
            scene_files.append(dest)
        else:
            print(f"  ⚠️  Skipping {sid}")

        time.sleep(0.3)

    if not scene_files:
        raise RuntimeError("No audio files generated.")

    print(f"\n  🔗 Combining {len(scene_files)} scenes...")
    full_audio = combine_audio_files(scene_files, audio_dir)

    if not full_audio:
        raise RuntimeError("Audio concat failed.")

    size_mb = full_audio.stat().st_size / 1_000_000
    print(f"  ✅ Voiceover ready: {full_audio} ({size_mb:.1f} MB)")
    return full_audio
