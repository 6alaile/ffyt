# Football Channel Pipeline

Automated pipeline: config JSON → HTML composition → voiceover → stock clips → HyperFrames render → YouTube.

```
configs/wc2026_ep01.json
        ↓
generate_html.py        (HTML composition + GSAP keyframes)
        ↓
fetch_clips.py          (Pixabay, with Pexels fallback)
        ↓
generate_voiceover.py   (Edge TTS, silence-padded to scene duration)
        ↓
npx hyperframes render  (headless Chrome → MP4)
        ↓
upload.py               (YouTube Data API v3)
```

---

## One-time Setup

### 1. Clone & install locally
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
pip install -r requirements.txt
# HyperFrames is fetched on demand — no global install needed locally
```

### 2. Get a stock-footage API key
- **Pixabay** (primary) — free at [pixabay.com/api/docs](https://pixabay.com/api/docs)
- **Pexels** (fallback, optional) — free at [pexels.com/api](https://www.pexels.com/api/)
- Set one or both as `PIXABAY_API_KEY` / `PEXELS_API_KEY` in your environment and in GitHub Secrets

### 3. Set up YouTube OAuth (run once, locally)
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. APIs & Services → Enable **YouTube Data API v3**
3. Credentials → Create OAuth 2.0 Client ID → **Desktop app**
4. Note the `Client ID` and `Client Secret`
5. Generate a refresh token locally:
   ```bash
   pip install google-auth-oauthlib
   python -c "
   from google_auth_oauthlib.flow import InstalledAppFlow
   flow = InstalledAppFlow.from_client_config({
     'installed': {
       'client_id': 'YOUR_CLIENT_ID',
       'client_secret': 'YOUR_CLIENT_SECRET',
       'auth_uri':  'https://accounts.google.com/o/oauth2/auth',
       'token_uri': 'https://oauth2.googleapis.com/token',
       'redirect_uris': ['http://localhost']
     }
   }, scopes=['https://www.googleapis.com/auth/youtube.upload'])
   creds = flow.run_local_server(port=0)
   print('REFRESH TOKEN:', creds.refresh_token)
   "
   ```
   A browser opens, you log in with the Google account that owns your channel, and the snippet prints the refresh token.

### 4. Add GitHub Secrets

In your repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|---|---|
| `PIXABAY_API_KEY` | Your Pixabay API key (or `PEXELS_API_KEY` for fallback) |
| `YOUTUBE_CLIENT_ID` | OAuth client ID from step 3 |
| `YOUTUBE_CLIENT_SECRET` | OAuth client secret from step 3 |
| `YOUTUBE_REFRESH_TOKEN` | Refresh token printed by the snippet in step 3 |

---

## Running a Video

### Locally
```bash
python pipeline.py --config configs/wc2026_ep01.json
python pipeline.py --config configs/wc2026_ep01.json --skip-upload
python pipeline.py --config configs/wc2026_ep01.json --format portrait     # 1080×1920 Shorts
```

The final video lands at `output_raw.mp4` in your repo root. `--skip-upload` produces the file without pushing to YouTube.

### GitHub Actions
1. Go to your repo → **Actions** tab
2. Select **Produce Video**
3. Click **Run workflow**
4. Pick a config filename (e.g. `wc2026_ep01.json`) and a format (`landscape` or `portrait`)
5. Click **Run workflow**

The rendered video is also saved as a GitHub Actions artifact (7-day retention).

---

## Adding a New Video

1. Copy `configs/wc2026_ep01.json` → `configs/wc2026_ep02.json`
2. Update `title`, the `youtube` block, and the `scenes[]` array
3. Commit and push
4. Run via GitHub Actions (or locally with `python pipeline.py --config ...`)

### Config structure
```json
{
  "title": "My Video Title",
  "channel": "@yourhandle",
  "youtube": {
    "description": "Full description...",
    "tags": ["tag1", "tag2"],
    "category": "Sports",
    "made_for_kids": false
  },
  "scenes": [
    {
      "id": "01_hook",
      "template": "impact_statement",
      "duration": 8,
      "clip_query": "soccer stadium crowd cheering",
      "voiceover": "Narration text for TTS — Edge TTS will pad or trim to fit 'duration' seconds.",
      "section_label": "01 — THE OPEN",
      "data": {
        "eyebrow": "// THE RECKONING",
        "line1": "EVERY WORLD CUP GETS CALLED",
        "line2": "THIS ONE",
        "line2_accent": "ACTUALLY IS.",
        "subhead": "// 4 MINUTES // 8 REASONS // 1 VERDICT",
        "footer_left": "JUNE 11, 2026 — JULY 19, 2026",
        "footer_right_pill": "PROOF"
      }
    }
  ]
}
```

### Templates
| Template | When to use | Required `data` keys |
|---|---|---|
| `impact_statement` | Centred two-line hook with one accent word | `eyebrow`, `line1`, `line2`, `line2_accent`, `subhead`, `footer_left`, `footer_right_pill` |
| `stat_split` | Headline left, stat cards right | `eyebrow`, `headline`, `headline_accent`, `body`, `stats[]`, `footer_left`, `footer_right` |
| `title_card` | Giant centred title, optional names row | `eyebrow`, `headline`, `headline_accent`, `body`, `names[]`, `footer_left`, `footer_right` |
| `stat_focus` | Huge bordered number left, name+quote right | `stat_label`, `stat_value`, `stat_context`, `tag`, `name`, `quote`, `footer_left`, `footer_right_pill` |
| `three_column` | Three equal cards (great for host nations) | `eyebrow`, `headline`, `cards[]`, `footer_left`, `footer_right` |
| `tag_list` | Centred headline with horizontal tag chips | `eyebrow`, `headline`, `headline_accent`, `body`, `tags[]`, `footer_left`, `footer_right` |
| `cta` | Subscribe / call-to-action screen | `badge`, `headline`, `body`, `sub_bottom`, `footer_left`, `footer_right` |

See `scripts/generate_html.py:126-320` for the exact HTML each template emits and `scripts/generate_html.py:388-479` for the matching GSAP keyframes.

---

## Voice Options (all free via Edge TTS)

| Voice | Style |
|---|---|
| `en-US-GuyNeural` | Deep, authoritative (default) |
| `en-US-ChristopherNeural` | Smooth, broadcast |
| `en-GB-RyanNeural` | British, punchy |
| `en-US-EricNeural` | Warm, conversational |

Pass `--voice <name>` to `generate_voiceover.py` (or change the default in `scripts/generate_voiceover.py:188`).

---

## Upgrading TTS Later

When you want a paid voice provider:
1. Replace `synthesize()` in `scripts/generate_voiceover.py:62` — the surrounding pipeline (per-scene synthesis → silence-pad to scene duration → concatenate) doesn't change.
2. Add the new provider's API key to GitHub Secrets.
3. The `voiceover` field in the config stays the same.

---

## GitHub Actions Limits (free tier)

| | Free |
|---|---|
| Minutes/month | 2,000 |
| Per video run | ~10–15 min (dominated by headless-Chromium render) |
| Videos/month | ~130–200 ✅ |
