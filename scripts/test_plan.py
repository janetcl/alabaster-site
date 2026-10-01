#!/usr/bin/env python3
"""Build the site, screenshot every page, and write docs/test-plan/README.md.

Run before every commit that goes to GitHub:

    python3 scripts/test_plan.py

Captures each page at desktop (1440px) and phone (390px) width with headless
Google Chrome, saves JPEGs to docs/test-plan/, and writes a checklist that
links them. Also fails if any page still contains an unrendered {{tag}} or
links to an image that does not exist.
"""
import functools
import http.server
import re
import shutil
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
OUT = ROOT / "docs" / "test-plan"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT = 8799

PAGES = [
    ("", "Home"),
    ("sunday-services", "Sunday Services"),
    ("sermons", "Sermons"),
    ("who-we-are", "Who We Are"),
    ("what-we-believe", "What We Believe"),
    ("on-campus", "On Campus"),
    ("student-membership", "Student Membership"),
    ("fr-26", "Fall Retreat 2026"),
    ("events", "Events"),
    ("contact", "Contact"),
    ("donate", "Give"),
    ("gospel-forum-2023", "Gospel Forum 2023"),
]

CHECKS = [
    "Header logo, menu and Give button render; dropdowns list the right sub-pages",
    "Announcement bar shows the retreat and a correct countdown",
    "“This Sunday” shows next Sunday’s date (New York time)",
    "Addresses open Google Maps; Messenger / email / YouTube links work",
    "Latest sermons match the podcast feed",
    "Fall Retreat section: dates, Register and Schedule & FAQs buttons",
    "Phone width: no sideways scrolling, cards stack, buttons are thumb-sized",
    "Footer: addresses, Explore and Connect links",
]


def chrome(*args):
    return subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", *args],
                          capture_output=True, text=True, timeout=120)


def page_height(url, width):
    """Load the page in an iframe of the given width and report its full height."""
    probe = DIST / "_probe.html"
    probe.write_text(
        f'<!doctype html><body style="margin:0"><iframe id="f" src="{url}" style="width:{width}px;height:400px;border:0"></iframe>'
        '<pre id="h"></pre><script>f.onload=()=>setTimeout(()=>{h.textContent="H="+f.contentDocument.documentElement.scrollHeight},800)</script>'
    )
    out = chrome("--window-size=1600,900", "--virtual-time-budget=6000", "--dump-dom", f"http://localhost:{PORT}/_probe.html").stdout
    m = re.search(r"H=(\d+)", out)
    return int(m.group(1)) if m else 4000


def shoot(slug, width, path):
    url = f"/{slug}" if slug else "/"
    height = page_height(url, width)
    shell = DIST / "_shot.html"
    # Headless Chrome is never narrower than 500px, so centre narrow frames and crop.
    pad = max(0, (500 - width) // 2)
    shell.write_text(f'<!doctype html><body style="margin:0;overflow:hidden"><iframe src="{url}" style="width:{width}px;height:{height}px;border:0;display:block;margin-left:{pad}px"></iframe>')
    png = path.with_suffix(".png")
    chrome(f"--window-size={max(width, 500)},{height}", "--virtual-time-budget=6000",
           f"--screenshot={png}", f"http://localhost:{PORT}/_shot.html")
    if width < 500:
        subprocess.run(["sips", "-c", str(height), str(width), str(png)], capture_output=True)
    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "62", "-Z", str(min(height, 4000)),
                    str(png), "--out", str(path)], capture_output=True)
    png.unlink(missing_ok=True)


def static_checks():
    problems = []
    for html in DIST.rglob("*.html"):
        if html.name.startswith("_"):
            continue
        text = html.read_text()
        for tag in re.findall(r"\{\{[^}]*\}\}", text):
            problems.append(f"{html.relative_to(DIST)}: unrendered {tag}")
        for src in re.findall(r'(?:src|href)="(/[^"#?]+\.(?:webp|jpg|png|pdf|css|js))"', text):
            if not (DIST / src.lstrip("/")).exists():
                problems.append(f"{html.relative_to(DIST)}: missing file {src}")
    return problems


def main():
    subprocess.run([sys.executable, str(ROOT / "build.py")], check=True, capture_output=True)
    problems = static_checks()

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
    http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
    server = http.server.ThreadingHTTPServer(("localhost", PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    rows = []
    try:
        for slug, name in PAGES:
            key = slug or "home"
            shoot(slug, 1440, OUT / f"{key}-desktop.jpg")
            shoot(slug, 390, OUT / f"{key}-phone.jpg")
            rows.append((slug, name, key))
            print(f"captured /{slug}")
    finally:
        server.shutdown()
        for tmp in ("_probe.html", "_shot.html"):
            (DIST / tmp).unlink(missing_ok=True)

    lines = [
        "# Test plan",
        "",
        f"Generated {datetime.now():%Y-%m-%d %H:%M} by `scripts/test_plan.py` from a fresh build.",
        "",
        "## Automated checks",
        "",
        "- " + ("All pages rendered with no leftover template tags and no missing files." if not problems
                else "**Problems found:**\n" + "\n".join(f"  - {p}" for p in problems)),
        "",
        "## Manual checks",
        "",
        *[f"- [ ] {c}" for c in CHECKS],
        "",
        "## Screenshots",
        "",
        "| Page | Desktop (1440px) | Phone (390px) |",
        "| --- | --- | --- |",
        *[f"| [{name}](https://janetcl.github.io/alabaster-site/{slug}) | <img src=\"{key}-desktop.jpg\" width=\"420\"> | <img src=\"{key}-phone.jpg\" width=\"160\"> |"
          for slug, name, key in rows],
        "",
    ]
    (OUT / "README.md").write_text("\n".join(lines))
    print(f"Wrote {OUT / 'README.md'}")
    if problems:
        print("\n".join(problems))
        sys.exit(1)


if __name__ == "__main__":
    main()
