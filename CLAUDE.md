# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`ffyt` is the "Football Channel Pipeline" — an automated, config-driven video production system. A single JSON config drives a 5-stage pipeline that produces a narrated sports video and (optionally) uploads it to YouTube. Free-tier tooling throughout (Edge TTS for voice, Pixabay for stock footage, GitHub Actions for compute, YouTube Data API for upload).

## Pipeline architecture

`pipeline.py` is the orchestrator. It loads a config JSON, then calls three modules in `scripts/` sequentially:

1. **`scripts/voiceover.py`** → `generate_voiceover(config)` — Edge TTS generates one MP3 per scene, cached on disk, then ffmpeg concatenates them into `output/{video_id}/audio/full_voiceover.mp3`.
2. **`scripts/video.py`** → `produce_video(config, audio_path)` — does steps 2–4 of the README diagram in one function:
   - Searches Pixabay per scene, downloads raw clips (cached).
   - ffmpeg scales each clip to 1280×720, mutes its audio, and overlays a Pillow-rendered PNG caption.
   - ffmpeg concatenates processed clips into a silent video, then muxes in the voiceover.
3. **`scripts/upload.py`** → `upload_to_youtube(config, video_path)` — OAuth via either `youtube_token.pickle` (local) or `YOUTUBE_TOKEN_B64` env var (CI), then resumable upload with chunked progress bar. Optional thumbnail upload if `output/{video_id}/thumbnail.jpg` exists.

The `config: dict` object is the spine that flows through all three stages — scene list, voice, YouTube metadata all live in one JSON file.

## Running

Local (requires `ffmpeg` on PATH, `PIXABAY_API_KEY` env var, and `youtube_token.pickle` in repo root for upload):
```bash
pip install -r requirements.txt
python pipeline.py --config configs/video_01.json
python pipeline.py --config configs/video_01.json --skip-upload   # produce only
```

CI: `.github/workflows/produce_video.yml` is a `workflow_dispatch` job (manual trigger) that takes `config_file` and `skip_upload` inputs. It installs `ffmpeg` + `fonts-dejavu-core`, decodes the `YOUTUBE_TOKEN_B64` secret into a pickle, runs the pipeline, and uploads `output/**/` as a 7-day artifact. Per-run timeout 45 min; free tier budget is ~130–200 videos/month.

## One-time OAuth setup

Not committed to the repo — referenced in README only. Local flow: `client_secrets.json` in root → run `python scripts/setup_token.py` (referenced in README, not present in this checkout) → paste resulting base64 into `YOUTUBE_TOKEN_B64` GitHub Secret.

## Adding a new video

Copy `configs/video_01.json`, change `video_id`, `title`, `scenes[].id/text/query/duration/text_overlay/text_size`, and `youtube` block. Each scene needs `text` (TTS input), `query` (Pixabay search), `duration` (seconds), and optional `text_overlay` + `text_size` for on-screen caption. Pixabay is queried with `min_duration = scene.duration`, so a clip shorter than the scene is skipped.

## Key conventions

- **Caching is intentional.** All intermediate artifacts (`{scene_id}.mp3`, `{scene_id}_raw.mp4`, `{scene_id}_processed.mp4`) are skipped if they exist on disk. To re-run a stage, delete the relevant `output/{video_id}/` subdirectory. This makes partial re-runs cheap on the CI minute budget.
- **All outputs land under `output/{video_id}/`** (gitignored). The final deliverable is `output/{video_id}/{video_id}_FINAL.mp4`.
- **TTS provider is swappable.** README explicitly notes that upgrading to ElevenLabs later means replacing only `generate_scene_audio()` in `scripts/voiceover.py:32` — the rest of the pipeline doesn't know or care.
- **Font handling is cross-platform.** `make_text_overlay_png()` checks Ubuntu paths first (for CI), then Windows (`C:\Windows\Fonts\arialbd.ttf`), then falls back to Pillow's default font. The `fonts-dejavu-core` apt package in the workflow exists specifically to satisfy this.
- **No tests, no linter config.** This is a single-purpose automation script, not a library. There is nothing to run besides the pipeline itself.
- **Secrets must never be committed:** `client_secrets.json`, `youtube_token.pickle`, `.env` are all in `.gitignore`. The CI never sees them in plaintext — the token is stored as base64 and decoded at runtime.
