#!/usr/bin/env python3
"""
Helper script to get a Dropbox refresh token.

This is a one-time setup script to obtain refresh token credentials that never
expire. The script guides the user through the OAuth flow to authorize the app
and exchanges the authorization code for long-lived refresh tokens.

Usage:
    python src/get_refresh_token.py

The script will:
1. Prompt for Dropbox App Key and App Secret
2. Open browser for user authorization
3. Exchange authorization code for tokens
4. Optionally update .env file with credentials
"""

import webbrowser
from urllib.parse import urlencode

import requests
from dotenv import set_key

print("=" * 70)
print("   Dropbox Refresh Token Generator")
print("=" * 70)

print("\n[INFO] Step 1: Get your App Key and App Secret")
print("   1. Go to: https://www.dropbox.com/developers/apps")
print("   2. Select your app")
print("   3. Go to 'Settings' tab")
print("   4. Find 'App key' and 'App secret'")

app_key = input("\n   Enter your App Key: ").strip()
app_secret = input("   Enter your App Secret: ").strip()

if not app_key or not app_secret:
    print("\n[ERROR] App Key and App Secret are required!")
    exit(1)

print("\n[INFO] Step 2: Authorize the app")
print("   Opening browser for authorization...")

# Build authorization URL with offline access
params = {
    "client_id": app_key,
    "response_type": "code",
    "token_access_type": "offline",  # This is the key to getting refresh token!
}

auth_url = f"https://www.dropbox.com/oauth2/authorize?{urlencode(params)}"
print(f"\n   URL: {auth_url}\n")

# Open browser
webbrowser.open(auth_url)

print("   1. Click 'Allow' in the browser")
print("   2. You'll see an authorization code")
print("   3. Copy the entire code")

auth_code = input("\n   Enter the authorization code: ").strip()

if not auth_code:
    print("\n[ERROR] Authorization code is required!")
    exit(1)

print("\n[INFO] Step 3: Exchange code for refresh token...")

# Exchange authorization code for tokens
token_url = "https://api.dropbox.com/oauth2/token"
data = {
    "code": auth_code,
    "grant_type": "authorization_code",
    "client_id": app_key,
    "client_secret": app_secret,
}

try:
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    tokens = response.json()

    print("\n" + "=" * 70)
    print("   [SUCCESS] SUCCESS! Got your tokens!")
    print("=" * 70)

    print("\n[INFO] Add these to your .env file:\n")
    print(f"DROPBOX_APP_KEY={app_key}")
    print(f"DROPBOX_APP_SECRET={app_secret}")
    print(f"DROPBOX_REFRESH_TOKEN={tokens['refresh_token']}")
    print(f"DROPBOX_ACCESS_TOKEN={tokens['access_token']}")

    print("\n[TIP] The refresh token never expires!")
    print("   Your script can now run indefinitely without token errors.\n")

    # Offer to update .env automatically
    update = input("Update .env file automatically? (y/n): ").strip().lower()

    if update == "y":
        env_file = ".env"

        # Update .env file
        set_key(env_file, "DROPBOX_APP_KEY", app_key)
        set_key(env_file, "DROPBOX_APP_SECRET", app_secret)
        set_key(env_file, "DROPBOX_REFRESH_TOKEN", tokens["refresh_token"])
        set_key(env_file, "DROPBOX_ACCESS_TOKEN", tokens["access_token"])

        print(f"\n[SUCCESS] Updated {env_file} with new credentials!")
        print("   You can now run: uv run explore")

except requests.exceptions.RequestException as e:
    print(f"\n[ERROR] Error getting tokens: {e}")
    if hasattr(e.response, "text"):
        print(f"   Response: {e.response.text}")
    exit(1)

print("\n" + "=" * 70)
print("   [DONE] Setup complete!")
print("=" * 70)
