"""
scripts/upload.py
─────────────────────────────────────────────────────────────
Uploads a rendered video to YouTube using the YouTube Data API v3,
pulling title/description/tags from the config JSON.

Requires three GitHub Secrets (one-time setup, see bottom of file
for instructions on obtaining them):
  YOUTUBE_CLIENT_ID
  YOUTUBE_CLIENT_SECRET
  YOUTUBE_REFRESH_TOKEN

Usage:
  python scripts/upload.py \
    --video output_raw.mp4 \
    --config configs/wc2026_ep01.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    import subprocess
    print("Installing Google API client...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-q",
        "google-auth", "google-auth-oauthlib", "google-api-python-client"
    ])
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_credentials() -> Credentials:
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    missing = [name for name, val in [
        ("YOUTUBE_CLIENT_ID", client_id),
        ("YOUTUBE_CLIENT_SECRET", client_secret),
        ("YOUTUBE_REFRESH_TOKEN", refresh_token),
    ] if not val]

    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("   See the bottom of scripts/upload.py for setup instructions.")
        sys.exit(1)

    return Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )


def upload_video(video_path: Path, config: dict, privacy: str = "private"):
    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    yt_meta = config.get("youtube", {})
    title = config.get("title", "Untitled")
    description = yt_meta.get("description", "")
    tags = yt_meta.get("tags", [])
    category = yt_meta.get("category", "Sports")
    made_for_kids = yt_meta.get("made_for_kids", False)

    # Map common category names to YouTube category IDs
    category_map = {
        "Sports": "17",
        "Entertainment": "24",
        "Education": "27",
        "Gaming": "20",
        "Howto & Style": "26",
        "People & Blogs": "22",
    }
    category_id = category_map.get(category, "17")

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")

    print(f"📤 Uploading {video_path.name} → \"{title}\" ({privacy})")

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   ↳ {int(status.progress() * 100)}% uploaded")

    video_id = response.get("id")
    print(f"\n✅ Uploaded: https://youtu.be/{video_id}")
    print(f"   Privacy: {privacy} — change to 'public' in YouTube Studio when ready.")
    return video_id


def main():
    parser = argparse.ArgumentParser(description="Upload rendered video to YouTube")
    parser.add_argument("--video", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--privacy", default="private",
                         choices=["private", "unlisted", "public"],
                         help="Default 'private' — review before publishing")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}")
        sys.exit(1)

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    upload_video(video_path, config, privacy=args.privacy)


if __name__ == "__main__":
    main()


# ─────────────────────────────────────────────────────────────
# ONE-TIME SETUP — obtaining YOUTUBE_CLIENT_ID / SECRET / REFRESH_TOKEN
# ─────────────────────────────────────────────────────────────
#
# 1. Go to https://console.cloud.google.com/ → create a project
#    (or use an existing one).
#
# 2. Enable "YouTube Data API v3" under APIs & Services > Library.
#
# 3. Go to APIs & Services > Credentials > Create Credentials
#    > OAuth client ID > Application type: "Desktop app".
#    This gives you a CLIENT_ID and CLIENT_SECRET.
#
# 4. Run this locally (one-time, on your own machine, NOT in CI)
#    to generate a refresh token:
#
#    pip install google-auth-oauthlib
#
#    python -c "
#    from google_auth_oauthlib.flow import InstalledAppFlow
#    flow = InstalledAppFlow.from_client_config({
#        'installed': {
#            'client_id': 'YOUR_CLIENT_ID',
#            'client_secret': 'YOUR_CLIENT_SECRET',
#            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
#            'token_uri': 'https://oauth2.googleapis.com/token',
#            'redirect_uris': ['http://localhost']
#        }
#    }, scopes=['https://www.googleapis.com/auth/youtube.upload'])
#    creds = flow.run_local_server(port=0)
#    print('REFRESH TOKEN:', creds.refresh_token)
#    "
#
#    This opens a browser, asks you to log in with the Google account
#    that owns @6allerAlert, and prints a refresh token.
#
# 5. In your GitHub repo: Settings > Secrets and variables > Actions
#    > New repository secret. Add all three:
#      YOUTUBE_CLIENT_ID
#      YOUTUBE_CLIENT_SECRET
#      YOUTUBE_REFRESH_TOKEN
#
# Note: videos upload as "private" by default. Review each one in
# YouTube Studio and switch to "public" manually — or pass
# --privacy public once you trust the pipeline.
# ─────────────────────────────────────────────────────────────
