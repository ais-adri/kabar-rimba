#!/usr/bin/env python3
"""Rimba Kabar daily update: harvest recent news, merge, push.

Prints a short summary line when new items land; prints nothing when
there is nothing new (so a no_agent cron stays silent).
"""
import urllib.request, urllib.parse, xml.etree.ElementTree as ET
import json, re, sys, time, subprocess, os

REPO = os.path.expanduser("~/projects/flora-fauna-id")

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

def fetch(q):
    url = ("https://news.google.com/rss/search?q="
           + urllib.parse.quote(q + " when:2d") + "&hl=id&gl=ID&ceid=ID:id")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def parse(xml_bytes, category):
    from email.utils import parsedate_to_datetime
    out = []
    for item in ET.fromstring(xml_bytes).iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate")
        src_el = item.find("{https://news.google.com}source")
        source = src_el.text.strip() if src_el is not None and src_el.text else ""
        if not source:
            m = re.match(r"^(.*)\s+-\s+([^-]+)$", title)
            if m:
                title, source = m.group(1).strip(), m.group(2).strip()
        elif title.endswith(" - " + source):
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
    os.chdir(REPO)
    subprocess.run(["git", "pull", "--ff-only", "origin", "main"],
                   check=True, capture_output=True)
    path = "data/news.json"
    with open(path) as f:
        existing = json.load(f)
    seen = {key(x["title"]) for x in existing}
    added = []
    for cat, qs in QUERIES.items():
        for q in qs:
            try:
                items = parse(fetch(q), cat)
            except Exception as e:
                print(f"! {q}: {e}", file=sys.stderr)
                continue
            for it in items:
                if key(it["title"]) not in seen:
                    seen.add(key(it["title"]))
                    added.append(it)
            time.sleep(0.5)
    if not added:
        return  # silent — nothing new
    merged = existing + added
    merged.sort(key=lambda x: x["date"], reverse=True)
    with open(path, "w") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)
    subprocess.run(["git", "add", path], check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m",
                    f"Auto-update: +{len(added)} berita ({time.strftime('%Y-%m-%d')})"],
                   check=True, capture_output=True)
    subprocess.run(["git", "push", "origin", "main"],
                   check=True, capture_output=True)
    print(f"🌿 Rimba Kabar: +{len(added)} berita baru hari ini (total {len(merged)}) — sudah live di https://ais-adri.github.io/rimba-kabar/")

if __name__ == "__main__":
    main()
