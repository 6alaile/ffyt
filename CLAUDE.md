# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`ffyt` is the "Football Channel Pipeline" — an automated, config-driven video production system. A single JSON config drives a pipeline that produces a narrated sports short and (optionally) uploads it to YouTube. Free-tier tooling throughout: Edge TTS for voice, Pixabay (with Pexels fallback) for stock footage, GitHub Actions for compute, YouTube Data API for upload, **HeyGen HyperFrames** for HTML-to-MP4 rendering via headless Chrome.

## Pipeline architecture

`pipeline.py` is a thin local orchestrator — it loads the config and calls the four CLI entry points under `scripts/` in sequence. CI (`.github/workflows/produce_video.yml`) runs the same four steps as separate `run:` blocks rather than calling `pipeline.py`.

1. **`scripts/generate_html.py`** → builds two artefacts from the config:
   - `composition.html` — a thin parent that mounts each scene as a sub-composition
   - `compositions/scene_NN.html` — one self-contained HTML per scene, with hard-coded GSAP keyframes for the scene's `template` and a `START_NN` start time
   - The HTML is the source of truth for both layout and animation; the config only carries data.
2. **`scripts/fetch_clips.py`** → for each scene, queries Pixabay (falls back to Pexels), downloads the best clip, and ffmpeg-scales/mutes/loops/trims it to the format's resolution and the scene's `duration`. Outputs `assets/clips/{scene_id}_processed.mp4`; raw downloads cached under `assets/clips/_raw/`. **Skipped if the processed file already exists.**
3. **`scripts/generate_voiceover.py`** → Edge TTS synthesises one MP3 per scene's `voiceover` text, trims or silence-pads it to match the scene's `duration`, then concatenates into `assets/audio/full_voiceover.mp3`. Per-scene TTS cached under `assets/audio/_scenes/`. **Skipped per-scene if the file already exists.**
4. **`npx hyperframes render`** (CI step; `run_hyperframes_render()` locally) → headless Chrome renders the composition HTML to `output_raw.mp4` (30 fps, 4 workers). HyperFrames discovers sub-compositions via `data-composition-src` on the parent's mount divs.
5. **`scripts/upload.py`** → YouTube Data API v3 upload using three OAuth env vars (`YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`). Resumable chunked upload, prints progress. Uploads as `private` by default.

The `config: dict` object is the spine that flows through every stage. `title`, `youtube` block, and the `scenes[]` array (each with `template`, `clip_query`, `voiceover`, `duration`, `data`) all live in one JSON file.

## Running

Local (requires `ffmpeg` + `ffprobe` on PATH, `PIXABAY_API_KEY` and/or `PEXELS_API_KEY` env var, Node.js 22 with `npx hyperframes`, and the three YouTube env vars for upload):
```bash
pip install -r requirements.txt
npm install
python pipeline.py --config configs/wc2026_ep01.json
python pipeline.py --config configs/wc2026_ep01.json --skip-upload           # produce only
python pipeline.py --config configs/wc2026_ep01.json --format portrait        # 1080×1920 Shorts
```

CI: `.github/workflows/produce_video.yml` is a `workflow_dispatch` job with `config` and `format` (landscape|portrait) inputs. It installs `ffmpeg` + `fonts-dejavu-core` + Puppeteer's system deps, caches media/voiceover outputs keyed on `hashFiles(config)`, runs each script as a separate `run:` step, then uploads the final `output_raw.mp4` as a 7-day artifact before pushing to YouTube. Per-run timeout 60 min.

## One-time OAuth setup

Three GitHub Secrets (and the matching local env vars) — refresh-token flow, no pickle or base64:

| Variable | How to obtain |
|---|---|
| `YOUTUBE_CLIENT_ID` | GCP → APIs & Services → Credentials → Create OAuth 2.0 Client ID → **Desktop app** |
| `YOUTUBE_CLIENT_SECRET` | Same as above |
| `YOUTUBE_REFRESH_TOKEN` | Local one-time snippet — copy from `scripts/upload.py:151` and run it; it does an `InstalledAppFlow.run_local_server()` browser auth and prints the refresh token |

The `Credentials` object in `scripts/upload.py:60` uses the refresh token to mint a short-lived access token on every upload. The refresh token never expires unless revoked.

## Adding a new video

Copy `configs/wc2026_ep01.json`, change `title`, the `youtube` block, and the `scenes[]` array. Each scene needs:
- `id` — slug, used as the filename prefix for clips and audio
- `template` — one of `impact_statement`, `stat_split`, `title_card`, `stat_focus`, `three_column`, `tag_list`, `cta`
- `duration` — seconds (drives both the video budget and the voiceover pad/trim)
- `clip_query` — Pixabay search terms
- `voiceover` — narration text for Edge TTS
- `data` — template-specific payload (see `generate_html.py:126-320` for each template's expected keys)

Pixabay is queried with `min_duration = 3`, then ffmpeg `-stream_loop -1` re-uses the clip to fill longer scenes. A 4-second stock clip can cover a 22-second scene — it just loops.

## Key conventions

- **Caching is intentional, at two layers.** Per-scene artefacts (`{scene_id}_processed.mp4`, `{scene_id}_padded.mp3`) are skipped if they exist. The workflow additionally wraps the clip-download and voiceover steps in `actions/cache` keyed on `hashFiles(config)` so re-runs cost almost nothing. To re-run a stage, delete the relevant subdirectory under `assets/` or `compositions/`.
- **The HTML composition is the source of truth, not the config.** Animations are hard-coded GSAP keyframes in `generate_html.py:388-479` per template, not data-driven. Adding a new template means writing both a `tpl_*` HTML emitter and a `build_gsap()` branch.
- **Sub-composition pattern is required by HyperFrames.** Each scene is its own self-contained HTML mounted by the parent via `<div data-composition-src="compositions/scene_NN.html" data-start="..." data-duration="...">`. The parent has no scene content of its own.
- **Format affects more than dimensions.** `FORMATS` in `generate_html.py:86` sets `width`, `height`, and a `font_scale` (landscape 1.0, portrait 0.65). The `PORTRAIT_OVERRIDES` CSS chunk in the same file is only injected when `format=portrait` — it stacks layouts vertically and tightens paddings.
- **Voiceover timing is auto-corrected.** If TTS produces more text than the scene budget, it's trimmed; if less, silence is padded with `apad=whole_dur={duration}` to land exactly on the scene boundary. The script warns if the total differs from the config by more than 5s.
- **No tests, no linter.** Single-purpose automation script. CI uses `npx --yes hyperframes` (transient, not locked) and pulls Puppeteer from the `package.json` `devDependencies` so the `actions/setup-node` npm cache engages on re-runs.
- **Secrets must never be committed:** `client_secrets.json`, `youtube_token.pickle`, `.env` are all in `.gitignore`. The CI passes them as env vars; locally the OAuth flow uses your own `InstalledAppFlow` runtime.
- **Fonts come from Google Fonts, not the system.** Anton / Manrope / JetBrains Mono are pulled by the HTML composition; the `fonts-dejavu-core` apt package in the workflow is a safety net for headless Chrome, not used by the composition itself.
