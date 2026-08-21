#!/usr/bin/env python3
"""Backfill historical months into data/news.json via Google News RSS."""
import urllib.request, urllib.parse, xml.etree.ElementTree as ET
import json, re, sys, time
from email.utils import parsedate_to_datetime

QUERIES = {
    "kekayaan": [
        "keanekaragaman hayati Indonesia",
        "spesies baru ditemukan Indonesia",
        "flora fauna endemik Indonesia",
        "satwa endemik Indonesia",
    ],
    "ancaman": [
        "satwa liar terancam punah Indonesia",
        "deforestasi Indonesia",
        "perburuan liar Indonesia perdagangan satwa",
        "kebakaran hutan Indonesia satwa",
    ],
    "konservasi": [
        "konservasi satwa Indonesia",
        "taman nasional Indonesia konservasi",
        "rehabilitasi satwa Indonesia pelepasliaran",
    ],
}

# monthly windows to backfill (after inclusive, before exclusive)
WINDOWS = [
    ("2026-01-01", "2026-02-01"),
    ("2026-02-01", "2026-03-01"),
    ("2026-03-01", "2026-04-01"),
    ("2026-04-01", "2026-05-01"),
    ("2026-05-01", "2026-06-01"),
    ("2026-06-01", "2026-07-01"),
    ("2026-07-01", "2026-07-22"),  # fill gap before existing oldest 2026-07-21
]

def fetch(q):
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(q)
           + "&hl=id&gl=ID&ceid=ID:id")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def parse(xml_bytes, category):
    out = []
    root = ET.fromstring(xml_bytes)
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate")
        src_el = item.find("{https://news.google.com}source")
        source = src_el.text.strip() if src_el is not None and src_el.text else ""
        if not source:
            m = re.match(r"^(.*)\s+-\s+([^-]+)$", title)
            if m:
                title, source = m.group(1).strip(), m.group(2).strip()
        else:
            # strip trailing " - Source" from title if present
            if title.endswith(" - " + source):
                title = title[: -(len(source) + 3)].strip()
        if len(title) < 25 or not pub:
            continue
        try:
            date = parsedate_to_datetime(pub).strftime("%Y-%m-%d")
        except Exception:
            continue
        out.append({"title": title, "link": link, "date": date,
                    "source": source or "Google News", "category": category})
    return out

def key(t):
    return t.lower()[:58]

def main():
    with open("data/news.json") as f:
        existing = json.load(f)
    seen = {key(x["title"]) for x in existing}
    added = []
    for a, b in WINDOWS:
        for cat, qs in QUERIES.items():
            for q in qs:
                full_q = f"{q} after:{a} before:{b}"
                try:
                    items = parse(fetch(full_q), cat)
                except Exception as e:
                    print(f"  ! {full_q}: {e}", file=sys.stderr)
                    continue
                n = 0
                for it in items:
                    if a <= it["date"] < b and key(it["title"]) not in seen:
                        seen.add(key(it["title"]))
                        added.append(it)
                        n += 1
                time.sleep(0.5)
        print(f"window {a}..{b}: total added so far {len(added)}")
    merged = existing + added
    merged.sort(key=lambda x: x["date"], reverse=True)
    with open("data/news.json", "w") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)
    print(f"added {len(added)}, total {len(merged)}")

if __name__ == "__main__":
    main()
