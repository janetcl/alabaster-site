#!/usr/bin/env python3
"""Refresh src/data/sermons.json from the Alabaster Group podcast feed.

Uses Apple's public lookup API (no key needed). Episode titles start with a
YYMMDD code, e.g. "260830 Who Are My Brothers", which gives the sermon date.

Run by hand or on a schedule (see .github/workflows/update-sermons.yml).
"""
import json
import re
import urllib.request
from datetime import date
from pathlib import Path

PODCAST_ID = "1704492988"
OUT = Path(__file__).resolve().parent.parent / "src" / "data" / "sermons.json"
URL = f"https://itunes.apple.com/lookup?id={PODCAST_ID}&entity=podcastEpisode&limit=12"


def parse(title):
    m = re.match(r"(\d{2})(\d{2})(\d{2})\s+(.*)", title)
    if not m:
        return None
    y, mo, d, name = m.groups()
    when = date(2000 + int(y), int(mo), int(d))
    return {
        "title": name.strip(),
        "iso": when.isoformat(),
        "date": when.strftime("%b %-d"),
        "long": when.strftime("Sunday, %b %-d"),
    }


def main():
    with urllib.request.urlopen(URL, timeout=30) as resp:
        results = json.load(resp)["results"]
    episodes = []
    for r in results:
        if r.get("wrapperType") != "podcastEpisode":
            continue
        ep = parse(r.get("trackName", ""))
        if ep:
            ep["url"] = r.get("trackViewUrl", "")
            episodes.append(ep)
    episodes.sort(key=lambda e: e["iso"], reverse=True)
    if not episodes:
        raise SystemExit("No episodes found; leaving sermons.json unchanged.")
    data = {"latest": episodes[0], "earlier": episodes[1:3], "all": episodes}
    OUT.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Latest: {episodes[0]['title']} ({episodes[0]['date']})")


if __name__ == "__main__":
    main()
