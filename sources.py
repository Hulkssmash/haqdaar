"""Load official source texts and split them into chunks. Standard library only.

Each file in data/sources/*.md starts with a small header:
---
scheme_id: pser
source_url: https://...
checked_on: 2026-10-01
---
<official text copied by hand>
"""
from pathlib import Path

SOURCES_DIR = Path(__file__).parent / "data" / "sources"


def parse_source_file(path):
    text = Path(path).read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = parts[2]
    return meta, body.strip()


def chunk_text(body, max_chars=700):
    """Merge neighbouring paragraphs into chunks of at most about max_chars."""
    paras = [p.strip() for p in body.split("\n\n") if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if cur and len(cur) + len(p) + 2 > max_chars:
            chunks.append(cur)
            cur = p
        else:
            cur = f"{cur}\n\n{p}" if cur else p
    if cur:
        chunks.append(cur)
    return chunks


def load_all(sources_dir=None):
    d = Path(sources_dir) if sources_dir else SOURCES_DIR
    items = []
    for f in sorted(d.glob("*.md")):
        meta, body = parse_source_file(f)
        for i, ch in enumerate(chunk_text(body)):
            items.append({
                "id": f"{meta.get('scheme_id', f.stem)}-{i}",
                "text": ch,
                "scheme_id": meta.get("scheme_id", f.stem),
                "source_url": meta.get("source_url", ""),
                "checked_on": meta.get("checked_on", ""),
            })
    return items
