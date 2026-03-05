#!/usr/bin/env python3
"""
Extract paper metadata via Gemini 2.5 Flash and output nanograph JSONL.

Usage:
    python3 _graph/extract.py <pdf_path>              # Extract one paper, print JSONL to stdout
    python3 _graph/extract.py <pdf_path> --append     # Extract and append to seed.jsonl
    python3 _graph/extract.py --all                   # Extract all un-enriched papers
    python3 _graph/extract.py --all --append          # Extract all and append to seed.jsonl
    python3 _graph/extract.py --dry-run <pdf_path>    # Show what would be extracted (no API call)

Requires: GEMINI_API_KEY environment variable
No pip dependencies -- stdlib only.
"""

import json
import os
import sys
import base64
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

# --- Config ---

MODEL = "gemini-2.5-flash"
API_BASE = "https://generativelanguage.googleapis.com/v1beta"
READINGS_DIR = Path(__file__).parent.parent.resolve()
SEED_FILE = Path(__file__).parent / "seed.jsonl"
MAX_PDF_SIZE_MB = 20
REQUEST_DELAY_S = 4.5  # ~13 RPM, well under 15 RPM limit

TOPIC_FOLDERS = [
    "ai_consciousness_and_ethics",
    "bioprinting_and_biofabrication",
    "brain_plasticity_and_gliomas",
    "brain_preservation_and_ex_vivo_models",
    "computational_neuroscience",
    "consciousness_theories",
    "machine_learning_and_generative_models",
    "mind_uploading_and_digital_minds",
    "neural_interfaces_and_neuromodulation",
    "neural_regeneration_and_stem_cells",
    "neural_tissue_engineering_and_organoids",
    "neuromorphic_computing",
    "philosophy_of_mind",
    "theoretical_physics",
    "virtual_reality_and_simulation",
]


def load_seed_data():
    """Load existing nodes and edges from seed.jsonl."""
    papers = {}
    concepts = {}
    authors = {}
    enriched_slugs = set()

    if not SEED_FILE.exists():
        return papers, concepts, authors, enriched_slugs

    with open(SEED_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)

            if obj.get("type") == "Paper":
                slug = obj["data"]["slug"]
                papers[slug] = obj["data"]
            elif obj.get("type") == "Concept":
                slug = obj["data"]["slug"]
                concepts[slug] = obj["data"]
            elif obj.get("type") == "Author":
                slug = obj["data"]["slug"]
                authors[slug] = obj["data"]
            elif obj.get("edge") == "WrittenBy":
                enriched_slugs.add(obj["from"])

    return papers, concepts, authors, enriched_slugs


def make_author_slug(name):
    """Convert 'Giulio Tononi' to 'tononi-giulio'."""
    parts = name.strip().split()
    if len(parts) >= 2:
        return re.sub(r"[^a-z0-9-]", "", f"{parts[-1]}-{'-'.join(parts[:-1])}".lower())
    return re.sub(r"[^a-z0-9-]", "", parts[0].lower())


def make_concept_slug(name):
    """Convert 'Integrated Information Theory' to 'integrated-information-theory'."""
    slug = re.sub(r"[^a-z0-9\s-]", "", name.lower().strip())
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def build_prompt(paper_slug, paper_title, existing_concepts, paper_catalogue):
    """Build the extraction prompt."""

    concept_list = "\n".join(f"  - {s}: {c.get('name', s)}" for s, c in sorted(existing_concepts.items()))
    if not concept_list:
        concept_list = "  (none yet -- you will create the first ones)"

    # Build paper catalogue for citation matching (slug: title)
    catalogue_lines = []
    for slug, data in sorted(paper_catalogue.items()):
        if slug != paper_slug:
            catalogue_lines.append(f"  - {slug}: {data.get('title', slug)}")
    catalogue = "\n".join(catalogue_lines[:200])  # cap at 200 to stay in context

    return f"""You are extracting structured metadata from a scientific paper for a knowledge graph.

**Paper being processed:** {paper_slug}
**Cleaned title:** {paper_title}

Extract the following from this PDF:

1. **authors**: List of author names exactly as printed on the paper. Full names, not initials.
2. **year**: Publication year (from the paper, not from when it was added to the library).
3. **abstract**: A 2-3 sentence summary of the paper's main contribution. Keep it concise.
4. **concepts**: 3-7 key scientific concepts this paper *substantially* covers. Not passing mentions -- core topics.

   REUSE these existing concept slugs when they match:
{concept_list}

   For new concepts, use lowercase-hyphenated format (e.g. "cortical-plasticity", "whole-brain-emulation").
   Return both the slug and a human-readable name.

5. **cites_in_collection**: Check the paper's bibliography/references. Do any of these papers from our collection appear?

{catalogue}

   Return ONLY slugs of papers that are actually cited. Do NOT guess -- if unsure, omit.

Return ONLY valid JSON. No markdown fences. No explanation. This exact structure:
{{
  "authors": [{{"name": "Full Name"}}],
  "year": "2024",
  "abstract": "The abstract text...",
  "concepts": [{{"slug": "concept-slug", "name": "Concept Name"}}],
  "cites_in_collection": ["slug-of-cited-paper"]
}}"""


def call_gemini(pdf_path, prompt):
    """Send PDF + prompt to Gemini 2.5 Flash, return parsed JSON."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    # Read and encode PDF
    pdf_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    if pdf_size_mb > MAX_PDF_SIZE_MB:
        print(f"Warning: {pdf_path} is {pdf_size_mb:.1f}MB (max {MAX_PDF_SIZE_MB}MB), skipping", file=sys.stderr)
        return None

    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode("utf-8")

    url = f"{API_BASE}/models/{MODEL}:generateContent?key={api_key}"

    payload = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "application/pdf", "data": pdf_b64}},
                {"text": prompt},
            ]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
        }
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        print(f"API error {e.code}: {body[:500]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None

    # Extract text from response
    try:
        text = result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        print(f"Unexpected response structure: {json.dumps(result)[:500]}", file=sys.stderr)
        return None

    # Parse JSON from response (strip markdown fences if present)
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}\nRaw response:\n{text[:1000]}", file=sys.stderr)
        return None


def extraction_to_jsonl(extraction, paper_slug, paper_title, paper_folder, paper_added, existing_concepts, existing_authors):
    """Convert Gemini extraction to JSONL lines for seed.jsonl."""
    lines = []

    if not extraction:
        return lines

    # Update Paper node with year and abstract
    update_data = {"slug": paper_slug, "title": paper_title, "folder": paper_folder, "added": paper_added}
    if extraction.get("year"):
        update_data["year"] = extraction["year"]
    if extraction.get("abstract"):
        update_data["abstract"] = extraction["abstract"]

    lines.append(json.dumps({"type": "Paper", "data": update_data}))

    # Author nodes + WrittenBy edges
    for author in extraction.get("authors", []):
        name = author.get("name", "").strip()
        if not name:
            continue
        slug = make_author_slug(name)
        if slug not in existing_authors:
            lines.append(json.dumps({"type": "Author", "data": {"slug": slug, "name": name}}))
            existing_authors[slug] = {"slug": slug, "name": name}
        lines.append(json.dumps({"edge": "WrittenBy", "from": paper_slug, "to": slug}))

    # Concept nodes + Covers edges
    for concept in extraction.get("concepts", []):
        slug = concept.get("slug", "")
        name = concept.get("name", "")
        if not slug:
            slug = make_concept_slug(name) if name else ""
        if not slug:
            continue
        if slug not in existing_concepts:
            lines.append(json.dumps({"type": "Concept", "data": {"slug": slug, "name": name or slug}}))
            existing_concepts[slug] = {"slug": slug, "name": name or slug}
        lines.append(json.dumps({"edge": "Covers", "from": paper_slug, "to": slug}))

    # Cites edges (only for papers in collection)
    for cited_slug in extraction.get("cites_in_collection", []):
        if cited_slug and cited_slug != paper_slug:
            lines.append(json.dumps({"edge": "Cites", "from": paper_slug, "to": cited_slug}))

    return lines


def find_pdf_path(paper_slug, papers):
    """Find the PDF file for a given paper slug."""
    folder = papers.get(paper_slug, {}).get("folder", "")
    if folder:
        path = READINGS_DIR / folder / f"{paper_slug}.pdf"
        if path.exists():
            return path
    # Fallback: search all folders
    for tf in TOPIC_FOLDERS:
        path = READINGS_DIR / tf / f"{paper_slug}.pdf"
        if path.exists():
            return path
    return None


def process_paper(pdf_path, papers, concepts, authors):
    """Process a single paper and return JSONL lines."""
    paper_slug = Path(pdf_path).stem
    paper_data = papers.get(paper_slug, {})
    paper_title = paper_data.get("title", paper_slug)
    paper_folder = paper_data.get("folder", "")
    paper_added = paper_data.get("added", "")

    print(f"  Extracting: {paper_slug}", file=sys.stderr)

    prompt = build_prompt(paper_slug, paper_title, concepts, papers)
    extraction = call_gemini(str(pdf_path), prompt)

    if not extraction:
        print(f"  FAILED: {paper_slug}", file=sys.stderr)
        return []

    lines = extraction_to_jsonl(extraction, paper_slug, paper_title, paper_folder, paper_added, concepts, authors)

    author_count = len(extraction.get("authors", []))
    concept_count = len(extraction.get("concepts", []))
    cites_count = len(extraction.get("cites_in_collection", []))
    print(f"  OK: {author_count} authors, {concept_count} concepts, {cites_count} citations", file=sys.stderr)

    return lines


def main():
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    append_mode = "--append" in args
    all_mode = "--all" in args
    dry_run = "--dry-run" in args
    pdf_args = [a for a in args if not a.startswith("--")]

    papers, concepts, authors, enriched_slugs = load_seed_data()

    all_lines = []

    if all_mode:
        # Process all un-enriched papers
        unenriched = [slug for slug in papers if slug not in enriched_slugs]
        total = len(unenriched)
        print(f"Found {total} un-enriched papers (of {len(papers)} total)", file=sys.stderr)

        if dry_run:
            for slug in unenriched:
                print(f"  Would extract: {slug}")
            sys.exit(0)

        for i, slug in enumerate(unenriched):
            pdf_path = find_pdf_path(slug, papers)
            if not pdf_path:
                print(f"  SKIP (no PDF): {slug}", file=sys.stderr)
                continue

            print(f"[{i+1}/{total}]", file=sys.stderr)
            lines = process_paper(pdf_path, papers, concepts, authors)

            # Write incrementally to survive timeouts
            if append_mode and lines:
                with open(SEED_FILE, "a") as f:
                    for line in lines:
                        f.write(line + "\n")
            else:
                all_lines.extend(lines)

            if i < total - 1:
                time.sleep(REQUEST_DELAY_S)

    else:
        # Process specific PDF(s)
        for pdf_arg in pdf_args:
            pdf_path = Path(pdf_arg).resolve()
            if not pdf_path.exists():
                print(f"Error: {pdf_path} not found", file=sys.stderr)
                continue

            if dry_run:
                paper_slug = pdf_path.stem
                print(f"Would extract: {paper_slug}")
                print(f"  File: {pdf_path}")
                print(f"  Size: {pdf_path.stat().st_size / (1024*1024):.1f}MB")
                continue

            lines = process_paper(pdf_path, papers, concepts, authors)
            all_lines.extend(lines)

    if dry_run:
        sys.exit(0)

    # Output
    if append_mode:
        with open(SEED_FILE, "a") as f:
            for line in all_lines:
                f.write(line + "\n")
        print(f"\nAppended {len(all_lines)} lines to {SEED_FILE}", file=sys.stderr)
        print("Run: nanograph load _graph/readings.nano --data _graph/seed.jsonl --mode merge", file=sys.stderr)
    else:
        for line in all_lines:
            print(line)

    print(f"\nTotal: {len(all_lines)} JSONL lines generated", file=sys.stderr)


if __name__ == "__main__":
    main()
