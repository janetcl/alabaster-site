#!/usr/bin/env python3
"""Find this Sunday's and last Sunday's livestream and write src/data/livestream.json.

The Sunday streams are unlisted, so they can't be found from the public
channel page. This uses the YouTube Data API as the channel owner
(read-only), with credentials from environment variables:

  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN

Get them once with scripts/youtube_auth.py (see docs/youtube-setup.md).
Without them the script exits quietly and leaves the file unchanged.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

OUT = Path(__file__).resolve().parent.parent / "src" / "data" / "livestream.json"
NY = ZoneInfo("America/New_York")


def access_token():
    body = urllib.parse.urlencode({
        "client_id": os.environ["YT_CLIENT_ID"],
        "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", body, timeout=30) as r:
        return json.load(r)["access_token"]


def broadcasts(token):
    """All of the channel's broadcasts (public, unlisted or private), newest first."""
    items, page = [], ""
    for _ in range(4):  # up to 200 broadcasts is plenty
        q = urllib.parse.urlencode({"part": "snippet,status", "broadcastStatus": "all",
                                    "broadcastType": "all", "maxResults": 50, "pageToken": page})
        req = urllib.request.Request(f"https://www.googleapis.com/youtube/v3/liveBroadcasts?{q}",
                                     headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        items += data.get("items", [])
        page = data.get("nextPageToken", "")
        if not page:
            break
    return items


def when(item):
    s = item["snippet"]
    stamp = s.get("actualStartTime") or s.get("scheduledStartTime")
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(NY) if stamp else None


def entry(item):
    d = when(item)
    return {
        "url": f"https://youtube.com/live/{item['id']}",
        "date": d.date().isoformat(),
        "label": d.strftime("%b %-d"),
        "title": item["snippet"].get("title", ""),
    }


def main():
    if not all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")):
        print("YouTube credentials not set; skipping livestream update.")
        return

    now = datetime.now(NY)
    next_sunday = (now + timedelta(days=(6 - now.weekday()) % 7)).date()

    upcoming = last = None
    for item in broadcasts(access_token()):
        d = when(item)
        if not d or d.weekday() != 6:  # Sunday services only
            continue
        status = item.get("status", {}).get("lifeCycleStatus", "")
        if d.date() == next_sunday and status != "revoked":
            upcoming = upcoming or item
        elif d.date() < next_sunday and status == "complete":
            if last is None or when(item) > when(last):
                last = item

    current = json.loads(OUT.read_text()) if OUT.exists() else {}
    data = {
        "upcoming": entry(upcoming) if upcoming else {"url": "", "date": next_sunday.isoformat(), "label": "", "title": ""},
        "last": entry(last) if last else current.get("last", {"url": "", "date": "", "label": "", "title": ""}),
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    }
    # Only rewrite when the links change, so the bot doesn't commit every run.
    if {k: v for k, v in data.items() if k != "updated"} == {k: v for k, v in current.items() if k != "updated"}:
        print("No change.")
        return
    OUT.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Upcoming: {data['upcoming']['url'] or '(not scheduled yet)'}  Last: {data['last']['url']}")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        sys.exit(f"YouTube API error {e.code}: {e.read().decode()[:400]}")
