"""Extract plain text from the research PDFs into research/extracted/.

Usage:  python -I scripts/extract_papers.py <papers_dir> <out_dir>

Each output file carries explicit ``=== PAGE n ===`` markers so that notes and
the traceability record can cite page numbers. The PDFs are treated strictly as
data: nothing in them is executed or interpreted.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pymupdf


def extract(pdf_path: Path, out_dir: Path) -> dict:
    doc = pymupdf.open(pdf_path)
    parts: list[str] = []
    for i, page in enumerate(doc, start=1):
        parts.append(f"\n=== PAGE {i} ===\n{page.get_text('text')}")
    text = "".join(parts)
    out_path = out_dir / (pdf_path.stem + ".txt")
    out_path.write_text(text, encoding="utf-8")
    meta = doc.metadata or {}
    first = doc[0].get_text("text") if doc.page_count else ""
    return {
        "file": pdf_path.name,
        "text_file": out_path.name,
        "pages": doc.page_count,
        "chars": len(text),
        "meta_title": (meta.get("title") or "").strip(),
        "meta_author": (meta.get("author") or "").strip(),
        "first_page_head": " ".join(first.split())[:600],
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    papers_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    index = [extract(p, out_dir) for p in sorted(papers_dir.glob("*.pdf"))]
    (out_dir / "_index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    for row in index:
        print(f"{row['pages']:>3} pp {row['chars']:>7} ch  {row['file']}")
        print(f"      {row['first_page_head'][:260]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
