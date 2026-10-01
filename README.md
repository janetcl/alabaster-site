# alabaster.org

The Alabaster Group website. Plain HTML and CSS, built with a small Python
script and no dependencies.

## Build and preview

    python3 build.py                 # writes dist/
    python3 -m http.server -d dist   # open http://localhost:8000

## Where things live

| What | Where |
| --- | --- |
| Pages (one per URL, same paths as the old site) | `src/pages/*.html` |
| Shared header, footer, cards, retreat block | `src/partials/*.html` |
| Service times, addresses, links, retreat details | `src/data/site.json` |
| Members on Who We Are | `src/data/members.json` |
| Campus contacts | `src/data/campuses.json` |
| Latest sermons (auto-updated) | `src/data/sermons.json` |
| Styles / script / images | `public/css`, `public/js`, `public/images` |

Most weekly edits (a new address, a retreat date, turning the top banner
off) are a one-line change in `src/data/site.json`.

## What updates itself

- **"This Sunday" dates** are worked out in the browser (New York time).
- **"Watch live"** points at `youtube.com/@AlabGrp/live`, which YouTube
  always sends to the current or next live stream.
- **Retreat countdown** reads `retreat.deadline` in `site.json`.
- **Latest sermons**: `scripts/update_sermons.py` reads the Apple Podcasts
  feed; `.github/workflows/update-sermons.yml` runs it twice a week and
  commits any change, which triggers a redeploy.

## Hosting (Cloudflare Pages, free)

- Build command: `python3 build.py`
- Output directory: `dist`
- `public/_redirects` keeps old Squarespace links working.

## Still to wire up

- Fall Retreat registration form: set `retreat.register_url` in `site.json`
  (e.g. a Tally or Google Form) — the old form lived inside Squarespace.
- Optional contact form (the old one was Squarespace; Messenger and email
  links are in place).
