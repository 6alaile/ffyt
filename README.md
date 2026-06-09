# Football Channel Pipeline

Automated pipeline: config JSON → voiceover → video → YouTube.

```
configs/video_03.json
        ↓
Edge TTS (free voiceover)
        ↓
Pixabay (stock clips)
        ↓
FFmpeg (stitch + merge)
        ↓
YouTube API (upload)
```

---

## One-time Setup

### 1. Clone & install locally
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
pip install -r requirements.txt
```

### 2. Get a Pixabay API key
- Register free at [pixabay.com/api/docs](https://pixabay.com/api/docs)
- Copy your API key

### 3. Set up YouTube OAuth (run once)
- Go to [console.cloud.google.com](https://console.cloud.google.com)
- APIs & Services → Enable **YouTube Data API v3**
- Credentials → Create OAuth 2.0 Client ID → Desktop app
- Download JSON → save as `client_secrets.json` in project root
- Run:
  ```bash
  python scripts/setup_token.py
  ```
- Follow browser login → copies base64 token to terminal

### 4. Add GitHub Secrets
In your repo: **Settings → Secrets → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `PIXABAY_API_KEY` | Your Pixabay API key |
| `YOUTUBE_TOKEN_B64` | Output from `setup_token.py` |

---

## Running a Video

### Locally
```bash
python pipeline.py --config configs/video_01.json
```

### GitHub Actions (cloud, free)
1. Go to your repo → **Actions** tab
2. Select **Produce & Upload Video**
3. Click **Run workflow**
4. Enter config filename, e.g. `video_01.json`
5. Click **Run workflow**

The final video is also saved as a GitHub Actions artifact (available for 7 days).

---

## Adding a New Video

1. Copy `configs/video_01.json` → `configs/video_02.json`
2. Update `video_id`, `title`, `scenes`, and `youtube` metadata
3. Commit and push
4. Run via GitHub Actions

### Config structure
```json
{
  "video_id": "video_02",
  "title": "My Video Title",
  "voice": "en-US-GuyNeural",
  "scenes": [
    {
      "id": "01_hook",
      "text": "Narration text for TTS",
      "query": "pixabay search query",
      "duration": 8,
      "text_overlay": "Text shown on screen",
      "text_size": 48
    }
  ],
  "youtube": {
    "title": "YouTube video title",
    "description": "Full description...",
    "tags": ["tag1", "tag2"],
    "privacy_status": "private"
  }
}
```

---

## Voice Options (all free via Edge TTS)

| Voice | Style |
|---|---|
| `en-US-GuyNeural` | Deep, authoritative (default) |
| `en-US-ChristopherNeural` | Smooth, broadcast |
| `en-GB-RyanNeural` | British, punchy |
| `en-US-EricNeural` | Warm, conversational |

Change via `"voice"` field in your config JSON.

---

## Upgrading TTS Later

When you hit monetisation and want ElevenLabs quality:
1. Replace `generate_scene_audio()` in `scripts/voiceover.py`
2. Add `ELEVENLABS_API_KEY` to GitHub Secrets
3. Everything else stays identical

---

## GitHub Actions Limits (free tier)

| | Free |
|---|---|
| Minutes/month | 2,000 |
| Per video run | ~10–15 min |
| Videos/month | ~130–200 ✅ |
