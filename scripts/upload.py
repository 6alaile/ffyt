"""
scripts/upload.py
Uploads the final video to YouTube using a saved OAuth token.

Token setup (run once locally):
  python scripts/setup_token.py
  → Follow browser auth
  → Encodes youtube_token.pickle to base64
  → Paste output into GitHub Secret: YOUTUBE_TOKEN_B64
"""

import base64
import os
import pickle
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

TOKEN_FILE = Path("youtube_token.pickle")


def load_credentials():
    """Load credentials from local pickle or from YOUTUBE_TOKEN_B64 env var (GitHub Actions)."""
    token_b64 = os.environ.get("YOUTUBE_TOKEN_B64", "")

    if token_b64:
        # Running in GitHub Actions — decode from secret
        token_bytes = base64.b64decode(token_b64)
        credentials = pickle.loads(token_bytes)
    elif TOKEN_FILE.exists():
        # Running locally
        with open(TOKEN_FILE, "rb") as f:
            credentials = pickle.load(f)
    else:
        print("❌ No YouTube token found.")
        print("   Locally: place youtube_token.pickle in the project root.")
        print("   GitHub Actions: set YOUTUBE_TOKEN_B64 secret.")
        print("   Run: python scripts/setup_token.py to generate the token.")
        sys.exit(1)

    # Refresh if expired
    if credentials.expired and credentials.refresh_token:
        print("  🔄 Refreshing YouTube token...")
        credentials.refresh(Request())

    return credentials


def build_youtube_client():
    credentials = load_credentials()
    return build("youtube", "v3", credentials=credentials)


def upload_video(youtube, config: dict, video_path: Path) -> str | None:
    meta = config.get("youtube", {})

    body = {
        "snippet": {
            "title":                meta.get("title", config.get("title", "Untitled")),
            "description":          meta.get("description", ""),
            "tags":                 meta.get("tags", []),
            "categoryId":           meta.get("category_id", "17"),  # 17 = Sports
            "defaultLanguage":      "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus":           meta.get("privacy_status", "private"),
            "selfDeclaredMadeForKids": False,
        },
    }

    if "publish_at" in meta:
        body["status"]["publishAt"] = meta["publish_at"]
        body["status"]["privacyStatus"] = "private"

    print(f"  Title: {body['snippet']['title']}")
    print(f"  Privacy: {body['status']['privacyStatus']}")
    print(f"  Size: {video_path.stat().st_size / 1_000_000:.1f} MB")

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 8,
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    response = None
    last_progress = -1

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                if progress != last_progress:
                    bar = "█" * (progress // 5) + "░" * (20 - progress // 5)
                    print(f"  [{bar}] {progress}%", end="\r")
                    last_progress = progress
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                import time
                print(f"\n  ⚠️  Server error {e.resp.status}, retrying...")
                time.sleep(5)
                continue
            raise

    print(f"\n  ✅ Uploaded!")
    video_id = response.get("id")
    print(f"  🔗 https://www.youtube.com/watch?v={video_id}")
    return video_id


def upload_thumbnail(youtube, video_id: str, thumbnail_path: Path):
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumbnail_path))
        ).execute()
        print("  ✅ Thumbnail set.")
    except HttpError as e:
        print(f"  ⚠️  Thumbnail failed: {e} — set manually in Studio.")


def upload_to_youtube(config: dict, video_path: Path):
    """Main entry point called by pipeline.py"""
    youtube = build_youtube_client()

    video_id = upload_video(youtube, config, video_path)
    if not video_id:
        raise RuntimeError("YouTube upload failed.")

    # Optional thumbnail
    thumb_path = Path(f"output/{config['video_id']}/thumbnail.jpg")
    if thumb_path.exists():
        print("\n  🖼️  Uploading thumbnail...")
        upload_thumbnail(youtube, video_id, thumb_path)
    else:
        print("  ℹ️  No thumbnail found — add one at:")
        print(f"     output/{config['video_id']}/thumbnail.jpg")

    print(f"""
─────────────────────────────────────────
  📋 POST-UPLOAD CHECKLIST
  https://studio.youtube.com/video/{video_id}/edit
─────────────────────────────────────────
  ☐ Watch back end-to-end
  ☐ Set thumbnail if not auto-uploaded
  ☐ Add to playlist
  ☐ Change Private → Public when ready
  ☐ Share to socials
─────────────────────────────────────────
""")
