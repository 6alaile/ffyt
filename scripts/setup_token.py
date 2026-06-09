"""
scripts/setup_token.py
Run this ONCE locally to authenticate with YouTube and generate
the base64 token string for GitHub Secrets.

Requirements:
  - client_secrets.json in project root (from Google Cloud Console)
  - pip install google-auth google-auth-oauthlib google-api-python-client

Usage:
  python scripts/setup_token.py
"""

import base64
import pickle
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

CLIENT_SECRETS = Path("client_secrets.json")
TOKEN_FILE = Path("youtube_token.pickle")


def main():
    print("=" * 60)
    print("  YouTube Token Setup")
    print("=" * 60)

    if not CLIENT_SECRETS.exists():
        print(f"\n❌ client_secrets.json not found.")
        print("   1. Go to console.cloud.google.com")
        print("   2. APIs & Services → Credentials → Create OAuth 2.0 Client ID")
        print("   3. Application type: Desktop app")
        print("   4. Download JSON → save as client_secrets.json here")
        return

    print("\n  Opening browser for Google authentication...")
    print("  Sign in with the Google account that owns your YouTube channel.\n")

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
    credentials = flow.run_local_server(port=0)

    # Save locally
    with open(TOKEN_FILE, "wb") as f:
        pickle.dump(credentials, f)
    print(f"\n  ✅ Token saved locally: {TOKEN_FILE}")

    # Encode for GitHub
    with open(TOKEN_FILE, "rb") as f:
        token_b64 = base64.b64encode(f.read()).decode("utf-8")

    print("\n" + "=" * 60)
    print("  GITHUB SECRET VALUE")
    print("  Copy everything between the dashes into:")
    print("  GitHub repo → Settings → Secrets → Actions")
    print("  Secret name: YOUTUBE_TOKEN_B64")
    print("=" * 60)
    print(f"\n{token_b64}\n")
    print("=" * 60)
    print("  Done! You won't need to run this again unless the token expires.")
    print("  If it does expire, just run this script again and update the secret.")


if __name__ == "__main__":
    main()
