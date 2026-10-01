#!/usr/bin/env python3
"""Build the Alabaster Group site into dist/.

No dependencies: uses only the Python standard library.

  src/layout.html        page shell (head, header, footer)
  src/partials/*.html    pieces included with {{> name}}
  src/pages/*.html       one file per page; front matter between --- lines
  src/data/*.json        data available as {{site.x}}, {{sermons.x}}
  public/                copied as-is (css, js, images)

Template syntax:
  {{a.b.c}}                       value lookup (HTML is inserted as-is)
  {{> name}}                      include src/partials/name.html
  {{#if a.b}} ... {{/if}}         keep block when value is truthy
  {{#each a.b}} {{this.x}} {{/each}}
"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"
DIST = ROOT / "dist"


def lookup(ctx, path):
    cur = ctx
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def render(text, ctx, depth=0):
    if depth > 10:
        raise RuntimeError("Template nesting too deep")

    def include(m):
        return render((SRC / "partials" / f"{m.group(1)}.html").read_text(), ctx, depth + 1)

    text = re.sub(r"\{\{>\s*([\w-]+)\s*\}\}", include, text)

    def each(m):
        items = lookup(ctx, m.group(1)) or []
        return "".join(render(m.group(2), {**ctx, "this": item}, depth + 1) for item in items)

    text = re.sub(r"\{\{#each\s+([\w.]+)\s*\}\}(.*?)\{\{/each\}\}", each, text, flags=re.S)

    def cond(m):
        return render(m.group(2), ctx, depth + 1) if lookup(ctx, m.group(1)) else ""

    text = re.sub(r"\{\{#if\s+([\w.]+)\s*\}\}(.*?)\{\{/if\}\}", cond, text, flags=re.S)

    def value(m):
        v = lookup(ctx, m.group(1))
        if v is None:
            raise KeyError(f"Missing template value: {m.group(1)}")
        return str(v)

    return re.sub(r"\{\{\s*([\w.]+)\s*\}\}", value, text)


def parse_page(path):
    raw = path.read_text()
    meta, body = {}, raw
    m = re.match(r"---\n(.*?)\n---\n(.*)", raw, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        body = m.group(2)
    return meta, body


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "public", DIST)

    data = {p.stem: json.loads(p.read_text()) for p in (SRC / "data").glob("*.json")}
    layout = (SRC / "layout.html").read_text()

    for page in sorted((SRC / "pages").glob("*.html")):
        meta, body = parse_page(page)
        ctx = {**data, "header": meta.get("header", "overlay"), **meta}
        ctx["title"] = meta.get("title", "Alabaster Group")
        ctx["description"] = meta.get("description", "A church in New York City and Boston devoted to Jesus Christ.")
        ctx["content"] = render(body, ctx)
        html = render(layout, ctx)
        out = DIST / "index.html" if page.stem == "index" else DIST / page.stem / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html)
        print(f"built /{'' if page.stem == 'index' else page.stem}")


if __name__ == "__main__":
    main()
