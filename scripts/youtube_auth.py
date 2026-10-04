#!/usr/bin/env python3
"""One-time sign-in so the site can read the channel's unlisted livestreams.

Run this on a computer where the YouTube channel owner can sign in:

    python3 scripts/youtube_auth.py CLIENT_ID CLIENT_SECRET

It opens a Google sign-in page asking for read-only access to YouTube.
Sign in with the account that owns (or manages) the Alabaster Group channel
and pick that channel. The script then prints a refresh token and, if the
GitHub CLI is available, offers to save all three values as repository
secrets (YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN).

See docs/youtube-setup.md for creating CLIENT_ID / CLIENT_SECRET.
"""
import http.server
import json
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import webbrowser

PORT = 8765
REDIRECT = f"http://localhost:{PORT}"
SCOPE = "https://www.googleapis.com/auth/youtube.readonly"


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    client_id, client_secret = sys.argv[1], sys.argv[2]

    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": REDIRECT, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent",
    })

    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in params.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<p style='font:18px sans-serif'>Done. You can close this tab and return to the terminal.</p>")

        def log_message(self, *args):
            pass

    print("Opening Google sign-in in your browser...\nIf it doesn't open, visit:\n" + url + "\n")
    webbrowser.open(url)
    server = http.server.HTTPServer(("localhost", PORT), Handler)
    while "code" not in result and "error" not in result:
        server.handle_request()
    if "error" in result:
        sys.exit(f"Sign-in was cancelled: {result['error']}")

    body = urllib.parse.urlencode({
        "code": result["code"], "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": REDIRECT, "grant_type": "authorization_code",
    }).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", body, timeout=30) as r:
        tokens = json.load(r)
    refresh = tokens.get("refresh_token")
    if not refresh:
        sys.exit("Google did not return a refresh token. Remove the app's access at "
                 "https://myaccount.google.com/permissions and run this again.")

    print("Signed in. Refresh token received.")
    secrets = {"YT_CLIENT_ID": client_id, "YT_CLIENT_SECRET": client_secret, "YT_REFRESH_TOKEN": refresh}
    if shutil.which("gh") and input("Save these as GitHub secrets for this repo now? [y/N] ").strip().lower() == "y":
        for name, value in secrets.items():
            subprocess.run(["gh", "secret", "set", name, "--body", value], check=True)
        print("Saved. The livestream workflow will pick them up on its next run.")
    else:
        print("\nAdd these three repository secrets on GitHub (Settings → Secrets and variables → Actions):")
        for name in secrets:
            print(f"  {name}")
        print("\nRefresh token (keep it private):\n" + refresh)


if __name__ == "__main__":
    main()
