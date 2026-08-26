#!/usr/bin/env python3
"""Canonicalise seed.jsonl: one Paper per slug, unique nodes and edges.

Reads _graph/seed.jsonl, unions duplicate Paper nodes for the same slug,
deduplicates other nodes by (type, slug) and edges by (edge, from, to),
and writes a temp file. Replaces seed.jsonl only with --write.

Dry-run (default) prints what would be squashed and does not write.

Usage:
    python3 _graph/build_seed.py
    python3 _graph/build_seed.py --write
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

SEED_DEFAULT = Path(__file__).parent / "seed.jsonl"

# Union these Paper fields when several extract.py modes append the same slug.
PAPER_FIELDS = (
    "year",
    "authors",
    "doi",
    "arxiv_id",
    "abstract",
    "thesis",
    "study_type",
    "title",
    "folder",
    "added",
)


def dumps(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(", ", ": "))


def nonempty(value: Any) -> bool:
    return value is not None and value != ""


def merge_fields(
    dest: dict[str, Any],
    src: dict[str, Any],
    fields: tuple[str, ...] | None,
) -> list[str]:
    """Copy missing fields from src into dest. Return filled field names.

    First non-empty value wins. Conflicting non-empty values are left as-is
    on dest and reported by the caller via a separate check.
    """
    filled: list[str] = []
    keys = fields if fields is not None else tuple(src.keys())
    for key in keys:
        if key == "slug" or key not in src:
            continue
        incoming = src[key]
        if not nonempty(incoming):
            continue
        if key not in dest or not nonempty(dest.get(key)):
            dest[key] = incoming
            filled.append(key)
    return filled


def conflicts(dest: dict[str, Any], src: dict[str, Any], fields: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for key in fields:
        if key not in src:
            continue
        a, b = dest.get(key), src.get(key)
        if nonempty(a) and nonempty(b) and a != b:
            found.append(key)
    return found


def load_records(path: Path) -> list[tuple[str, dict[str, Any]]]:
    records: list[tuple[str, dict[str, Any]]] = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            raw = line.rstrip("\n")
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            if not isinstance(obj, dict):
                raise SystemExit(f"{path}:{lineno}: expected a JSON object")
            records.append((raw, obj))
    return records


def canonicalise(records: list[tuple[str, dict[str, Any]]]) -> tuple[list[str], dict[str, Any]]:
    kept: list[str | None] = []
    paper_at: dict[str, int] = {}
    paper_data: dict[str, dict[str, Any]] = {}
    node_at: dict[tuple[str, str], int] = {}
    node_data: dict[tuple[str, str], dict[str, Any]] = {}
    edge_at: dict[tuple[str, str, str], int] = {}

    dropped_papers: list[str] = []
    filled_papers: dict[str, list[str]] = {}
    paper_conflicts: dict[str, list[str]] = {}
    dropped_nodes: list[tuple[str, str]] = []
    filled_nodes: dict[tuple[str, str], list[str]] = {}
    dropped_edges: list[tuple[str, str, str]] = []
    skipped: list[str] = []

    for raw, obj in records:
        if "type" in obj:
            data = obj.get("data")
            if not isinstance(data, dict) or "slug" not in data:
                skipped.append(raw)
                kept.append(raw)
                continue
            slug = data["slug"]
            ntype = obj["type"]
            if ntype == "Paper":
                if slug in paper_at:
                    idx = paper_at[slug]
                    dest = paper_data[slug]
                    clash = conflicts(dest, data, PAPER_FIELDS)
                    if clash:
                        paper_conflicts.setdefault(slug, [])
                        for field in clash:
                            if field not in paper_conflicts[slug]:
                                paper_conflicts[slug].append(field)
                    filled = merge_fields(dest, data, PAPER_FIELDS)
                    if filled:
                        filled_papers.setdefault(slug, []).extend(filled)
                        merged = {"type": "Paper", "data": dest}
                        kept[idx] = dumps(merged)
                    dropped_papers.append(slug)
                    kept.append(None)
                else:
                    merged_data = dict(data)
                    paper_at[slug] = len(kept)
                    paper_data[slug] = merged_data
                    kept.append(raw)
            else:
                key = (ntype, slug)
                if key in node_at:
                    idx = node_at[key]
                    dest = node_data[key]
                    extra_fields = tuple(k for k in data.keys() if k != "slug")
                    filled = merge_fields(dest, data, extra_fields)
                    if filled:
                        filled_nodes.setdefault(key, []).extend(filled)
                        merged = {"type": ntype, "data": dest}
                        kept[idx] = dumps(merged)
                    dropped_nodes.append(key)
                    kept.append(None)
                else:
                    copied = dict(data)
                    node_at[key] = len(kept)
                    node_data[key] = copied
                    kept.append(raw)
        elif "edge" in obj:
            frm = obj.get("from")
            to = obj.get("to")
            if not isinstance(frm, str) or not isinstance(to, str):
                skipped.append(raw)
                kept.append(raw)
                continue
            key = (obj["edge"], frm, to)
            if key in edge_at:
                dropped_edges.append(key)
                kept.append(None)
            else:
                edge_at[key] = len(kept)
                kept.append(raw)
        else:
            skipped.append(raw)
            kept.append(raw)

    lines = [line for line in kept if line is not None]
    report = {
        "input_records": len(records),
        "output_records": len(lines),
        "dropped_papers": dropped_papers,
        "filled_papers": filled_papers,
        "paper_conflicts": paper_conflicts,
        "dropped_nodes": dropped_nodes,
        "filled_nodes": filled_nodes,
        "dropped_edges": dropped_edges,
        "skipped": len(skipped),
        "paper_count": len(paper_at),
        "changed": bool(
            dropped_papers
            or filled_papers
            or dropped_nodes
            or filled_nodes
            or dropped_edges
        ),
    }
    return lines, report


def print_report(report: dict[str, Any]) -> None:
    dropped_papers = report["dropped_papers"]
    filled_papers = report["filled_papers"]
    paper_conflicts = report["paper_conflicts"]
    dropped_nodes = report["dropped_nodes"]
    filled_nodes = report["filled_nodes"]
    dropped_edges = report["dropped_edges"]

    print(f"input records: {report['input_records']}")
    print(f"output records: {report['output_records']}")
    print(f"unique Paper slugs: {report['paper_count']}")

    if dropped_papers:
        counts: dict[str, int] = {}
        for slug in dropped_papers:
            counts[slug] = counts.get(slug, 0) + 1
        print(f"duplicate Paper nodes dropped: {len(dropped_papers)} copies across {len(counts)} slugs")
        for slug, n in sorted(counts.items()):
            extra = ""
            if slug in filled_papers:
                extra = f" (filled {', '.join(filled_papers[slug])})"
            print(f"  {slug}: dropped {n} extra node(s){extra}")
    else:
        print("duplicate Paper nodes dropped: 0")

    if paper_conflicts:
        print("Paper field conflicts (kept first non-empty value):")
        for slug, fields in sorted(paper_conflicts.items()):
            print(f"  {slug}: {', '.join(fields)}")

    if dropped_nodes:
        print(f"duplicate other nodes dropped: {len(dropped_nodes)}")
        for ntype, slug in dropped_nodes:
            extra = ""
            key = (ntype, slug)
            if key in filled_nodes:
                extra = f" (filled {', '.join(filled_nodes[key])})"
            print(f"  {ntype} {slug}{extra}")
    else:
        print("duplicate other nodes dropped: 0")

    if dropped_edges:
        print(f"duplicate edges dropped: {len(dropped_edges)}")
        for edge, frm, to in dropped_edges:
            print(f"  {edge} {frm} -> {to}")
    else:
        print("duplicate edges dropped: 0")

    if report["skipped"]:
        print(f"unrecognised records kept as-is: {report['skipped']}")

    if not report["changed"]:
        print("nothing to squash")


def write_seed(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix="seed.jsonl.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            for line in lines:
                tmp.write(line)
                tmp.write("\n")
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="replace seed.jsonl if canonicalisation changes it",
    )
    parser.add_argument(
        "--seed",
        type=Path,
        default=SEED_DEFAULT,
        help="path to seed.jsonl (default: _graph/seed.jsonl)",
    )
    args = parser.parse_args(argv)

    seed = args.seed
    if not seed.exists():
        print(f"error: {seed} not found", file=sys.stderr)
        return 1

    records = load_records(seed)
    lines, report = canonicalise(records)
    print_report(report)

    if not args.write:
        return 0

    if not report["changed"]:
        print(f"left {seed} unchanged")
        return 0

    write_seed(seed, lines)
    print(f"wrote {len(lines)} records to {seed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
