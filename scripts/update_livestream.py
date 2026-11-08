#!/usr/bin/env python3
"""Find this Sunday's and last Sunday's livestream and write src/data/livestream.json.

The Sunday streams are unlisted, so they can't be found from the public
channel page. This uses the YouTube Data API as the channel owner
(read-only), with credentials from environment variables:

  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN

Get them once with scripts/youtube_auth.py (see docs/youtube-setup.md).

Without them it falls back to the public "Alabaster Livestream" playlist that
alabaster.org's "Stream Live" button points at. The playlist holds the coming
Sunday's stream, titled "Alabaster Group Sunday Service - M/D/YY"; when it
moves on to the next week, the stream we had becomes "last Sunday".
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

OUT = Path(__file__).resolve().parent.parent / "src" / "data" / "livestream.json"
NY = ZoneInfo("America/New_York")
PLAYLIST = os.environ.get("YT_PLAYLIST_ID", "PL6p5JOJgexP-Y3p10ppQ-LsmqvayAP58k")


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


def playlist_streams():
    """(video id, service date, title) for each Sunday service in the public playlist."""
    req = urllib.request.Request(f"https://www.youtube.com/playlist?list={PLAYLIST}",
                                 headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US"})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", "replace")
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", page)
    if not m:
        raise RuntimeError("couldn't read the playlist page")
    found = []

    def walk(o):
        if isinstance(o, dict):
            vid = title = None
            if "playlistVideoRenderer" in o:
                r = o["playlistVideoRenderer"]
                vid, title = r.get("videoId"), "".join(t.get("text", "") for t in r.get("title", {}).get("runs", []))
            elif "lockupViewModel" in o:
                r = o["lockupViewModel"]
                vid = r.get("contentId")
                title = r.get("metadata", {}).get("lockupMetadataViewModel", {}).get("title", {}).get("content", "")
            d = re.search(r"Sunday Service\s*-\s*(\d{1,2})/(\d{1,2})/(\d{2,4})", title or "")
            if vid and d:
                mo, day, yr = (int(x) for x in d.groups())
                found.append((vid, datetime(yr + 2000 if yr < 100 else yr, mo, day).date(), title))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(json.loads(m.group(1)))
    return found


def from_playlist(next_sunday, current):
    """The same shape as the API path, built from the public playlist."""
    def make(vid, d, title):
        return {"url": f"https://youtube.com/live/{vid}", "date": d.isoformat(),
                "label": f"{d:%b} {d.day}", "title": title}

    upcoming = last = None
    for vid, d, title in playlist_streams():
        if d == next_sunday:
            upcoming = upcoming or make(vid, d, title)
        elif d < next_sunday and (last is None or d.isoformat() > last["date"]):
            last = make(vid, d, title)
    # The playlist only holds the current week, so last week's link is the one we saved.
    saved = current.get("upcoming", {})
    if saved.get("url") and saved.get("date", "") < next_sunday.isoformat():
        if last is None or saved["date"] > last["date"]:
            last = saved
    return upcoming, last


def main():
    now = datetime.now(NY)
    next_sunday = (now + timedelta(days=(6 - now.weekday()) % 7)).date()
    current = json.loads(OUT.read_text()) if OUT.exists() else {}

    if not all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")):
        print("No YouTube credentials; reading the public livestream playlist.")
        upcoming, last = from_playlist(next_sunday, current)
        write(upcoming, last, next_sunday, current)
        return

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

    write(entry(upcoming) if upcoming else None, entry(last) if last else None, next_sunday, current)


def write(upcoming, last, next_sunday, current):
    blank = {"url": "", "date": "", "label": "", "title": ""}
    last = last or current.get("last", blank)
    # Only offer "Missed last Sunday?" for last week's service, not an old one.
    if last.get("date", "") < (next_sunday - timedelta(days=7)).isoformat():
        last = blank
    data = {
        "upcoming": upcoming or {"url": "", "date": next_sunday.isoformat(), "label": "", "title": ""},
        "last": last,
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
