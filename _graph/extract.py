#!/usr/bin/env python3
"""
Extract structured content from scientific papers via Gemini 2.5 Flash.

Every mode produces JSONL for the knowledge graph (seed.jsonl).

Usage:
    python3 _graph/extract.py <pdf_path>                        # metadata (default)
    python3 _graph/extract.py <pdf_path> --mode figures         # figures and tables
    python3 _graph/extract.py <pdf_path> --mode claims          # claims and arguments
    python3 _graph/extract.py <pdf_path> --mode relations       # Extends/Contradicts
    python3 _graph/extract.py <pdf_path> --mode methods         # techniques and protocols
    python3 _graph/extract.py <pdf_path> --mode definitions     # definitions and axioms
    python3 _graph/extract.py <pdf_path> --mode open-questions  # open problems
    python3 _graph/extract.py <pdf_path> --append               # append JSONL to seed.jsonl
    python3 _graph/extract.py --all --mode figures --append     # batch mode
    python3 _graph/extract.py --dry-run <pdf_path>              # preview, no API call

Modes:
    metadata (default)  Paper, Author, Concept nodes + WrittenBy, Covers, Cites edges
    figures             Figure nodes + HasFigure edges
    claims              Claim nodes + MakesClaim edges + Paper.thesis
    relations           Extends / Contradicts edges
    methods             Technique nodes + UsesTechnique edges + Paper.study_type
    definitions         Definition nodes + HasDefinition edges
    open-questions      OpenQuestion nodes + Raises edges

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

# Edge type used by each mode to mark a paper as enriched.
# load_seed_data() builds a set per edge type; --all skips papers already present.
MODE_EDGE = {
    "metadata": "WrittenBy",
    "figures": "HasFigure",
    "claims": "MakesClaim",
    "relations": "Extends",
    "methods": "UsesTechnique",
    "definitions": "HasDefinition",
    "open-questions": "Raises",
}


# ─────────────────────────────────────────────
# Seed data
# ─────────────────────────────────────────────

def load_seed_data():
    """Load existing nodes and edges from seed.jsonl.

    Returns (papers, concepts, authors, techniques, enriched) where
    enriched maps edge-type -> set-of-paper-slugs that already have
    that edge.
    """
    papers = {}
    concepts = {}
    authors = {}
    techniques = {}
    enriched = {edge: set() for edge in MODE_EDGE.values()}

    if not SEED_FILE.exists():
        return papers, concepts, authors, techniques, enriched

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
            elif obj.get("type") == "Technique":
                slug = obj["data"]["slug"]
                techniques[slug] = obj["data"]

            edge_type = obj.get("edge")
            if edge_type in enriched:
                enriched[edge_type].add(obj["from"])

    return papers, concepts, authors, techniques, enriched


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


def make_technique_slug(name):
    """Convert 'Calcium Imaging' to 'calcium-imaging'."""
    slug = re.sub(r"[^a-z0-9\s-]", "", name.lower().strip())
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def build_paper_catalogue(papers, exclude_slug=""):
    """Build catalogue string of papers for cross-referencing prompts."""
    lines = []
    for slug, data in sorted(papers.items()):
        if slug != exclude_slug:
            lines.append(f"  - {slug}: {data.get('title', slug)}")
    return "\n".join(lines[:200])


# ─────────────────────────────────────────────
# Gemini API
# ─────────────────────────────────────────────

def call_gemini(pdf_path, prompt, max_tokens=8192):
    """Send PDF + prompt to Gemini 2.5 Flash, return parsed JSON."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

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
            "maxOutputTokens": max_tokens,
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

    try:
        text = result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        print(f"Unexpected response structure: {json.dumps(result)[:500]}", file=sys.stderr)
        return None

    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}\nRaw response:\n{text[:1000]}", file=sys.stderr)
        return None


def find_pdf_path(paper_slug, papers):
    """Find the PDF file for a given paper slug."""
    folder = papers.get(paper_slug, {}).get("folder", "")
    if folder:
        path = READINGS_DIR / folder / f"{paper_slug}.pdf"
        if path.exists():
            return path
    for tf in TOPIC_FOLDERS:
        path = READINGS_DIR / tf / f"{paper_slug}.pdf"
        if path.exists():
            return path
    return None


# ─────────────────────────────────────────────
# Prompt builders
# ─────────────────────────────────────────────

def build_metadata_prompt(ctx):
    """Prompt for metadata extraction (authors, year, abstract, concepts, citations)."""
    concept_list = "\n".join(
        f"  - {s}: {c.get('name', s)}" for s, c in sorted(ctx["concepts"].items())
    )
    if not concept_list:
        concept_list = "  (none yet -- you will create the first ones)"

    catalogue = build_paper_catalogue(ctx["papers"], ctx["paper_slug"])

    return f"""You are extracting structured metadata from a scientific paper for a knowledge graph.

**Paper being processed:** {ctx["paper_slug"]}
**Cleaned title:** {ctx["paper_title"]}

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


def build_figures_prompt(ctx):
    """Prompt for figure and table extraction."""
    return f"""You are extracting structured information about every figure and table from a scientific paper.

**Paper:** {ctx["paper_slug"]}
**Title:** {ctx["paper_title"]}

For EACH figure and table in this PDF, extract:
- **id**: Figure/table number as labelled (e.g. "Figure 1", "Table 2", "Fig. 3a")
- **caption**: The full caption text
- **type**: One of: diagram, chart, bar_chart, line_chart, scatter_plot, heatmap, micrograph, photograph, schematic, architecture, table, flowchart, graph, illustration, other
- **description**: What the figure/table shows -- axes, variables, data represented, visual structure. Be precise and technical.
- **key_data**: Array of notable quantitative values, measurements, or data points readable from the figure/table. For tables, include column headers and representative rows. Empty array if no quantitative data is readable.
- **significance**: How this figure/table supports the paper's argument (1-2 sentences)

Return ONLY valid JSON. No markdown fences. No explanation.
{{
  "figures": [
    {{
      "id": "Figure 1",
      "caption": "...",
      "type": "diagram",
      "description": "...",
      "key_data": ["..."],
      "significance": "..."
    }}
  ]
}}"""


def build_claims_prompt(ctx):
    """Prompt for claims and argumentative structure extraction."""
    return f"""You are extracting the argumentative structure from a scientific paper.

**Paper:** {ctx["paper_slug"]}
**Title:** {ctx["paper_title"]}

Extract:
1. **thesis**: The paper's central claim or main contribution (1-2 sentences).
2. **claims**: Each distinct claim the paper makes. For each:
   - **claim**: The claim stated precisely
   - **evidence_type**: One of: empirical, computational, theoretical, philosophical, mathematical, review
   - **support**: How the authors support this claim (specific experiments, proofs, arguments)
   - **strength**: Authors' own assessment where stated, or inferred: strong, moderate, preliminary, speculative
3. **assumptions**: Foundational premises the paper takes as given without arguing for them.
4. **structure**: Brief description of the overall argumentative flow -- what depends on what, the logical chain from premises to conclusion.

Return ONLY valid JSON. No markdown fences. No explanation.
{{
  "thesis": "...",
  "claims": [
    {{
      "claim": "...",
      "evidence_type": "empirical",
      "support": "...",
      "strength": "strong"
    }}
  ],
  "assumptions": ["..."],
  "structure": "..."
}}"""


def build_relations_prompt(ctx):
    """Prompt for Extends/Contradicts relationship detection."""
    catalogue = build_paper_catalogue(ctx["papers"], ctx["paper_slug"])

    return f"""You are identifying deep intellectual relationships between scientific papers in a research collection.

**Paper being analysed:** {ctx["paper_slug"]}
**Title:** {ctx["paper_title"]}

Here are the other papers in this collection:
{catalogue}

For each paper in the collection that this paper has a DIRECT intellectual relationship with, classify as:
- **extends**: This paper builds directly on, refines, or develops the ideas from the other paper. Not merely citing -- genuinely extending the work.
- **contradicts**: This paper argues against, refutes, or presents evidence conflicting with the other paper's claims.

Provide a brief justification (1-2 sentences) for each relationship.

Be conservative. Only flag relationships you are confident about from the paper's actual content. Merely citing a paper is NOT sufficient for "extends" -- there must be genuine intellectual continuation. Merely disagreeing on a minor point is not "contradicts" -- reserve this for substantive disagreements.

Return ONLY valid JSON. No markdown fences. No explanation.
{{
  "extends": [
    {{"slug": "paper-slug", "justification": "..."}}
  ],
  "contradicts": [
    {{"slug": "paper-slug", "justification": "..."}}
  ]
}}"""


def build_methods_prompt(ctx):
    """Prompt for experimental methods extraction."""
    technique_list = "\n".join(
        f"  - {s}: {t.get('name', s)}" for s, t in sorted(ctx["techniques"].items())
    )
    if not technique_list:
        technique_list = "  (none yet -- you will create the first ones)"

    return f"""You are extracting the methodology from a scientific paper in structured form.

**Paper:** {ctx["paper_slug"]}
**Title:** {ctx["paper_title"]}

Extract:
1. **study_type**: One or more of: in_vitro, in_vivo, ex_vivo, computational, theoretical, mathematical, philosophical, review, meta_analysis, clinical, case_study
2. **techniques**: Specific methods, assays, imaging modalities, algorithms, instruments, software, or analytical frameworks used in this paper. For each, provide both a slug and a human-readable name.

   REUSE these existing technique slugs when they match:
{technique_list}

   For new techniques, use lowercase-hyphenated format (e.g. "calcium-imaging", "patch-clamp-electrophysiology", "graph-neural-network").
   Include both experimental techniques AND computational tools/software.

Return ONLY valid JSON. No markdown fences. No explanation.
{{
  "study_type": ["computational", "theoretical"],
  "techniques": [{{"slug": "technique-slug", "name": "Technique Name", "category": "imaging|electrophysiology|computational|molecular|behavioural|statistical|instrument|software|other"}}]
}}"""


def build_definitions_prompt(ctx):
    """Prompt for definitions, axioms, and formal terminology extraction."""
    return f"""You are extracting formal definitions and terminology from a scientific paper.

**Paper:** {ctx["paper_slug"]}
**Title:** {ctx["paper_title"]}

Extract:
1. **definitions**: Formal or explicit definitions given in the paper. For each:
   - **term**: The term being defined
   - **definition**: The definition as stated or closely paraphrased
   - **section**: Where in the paper this appears (section name/number if available)
   - **formal**: true if mathematical/formal definition, false if prose

2. **axioms**: Axioms, postulates, principles, or foundational assumptions explicitly stated and named.
   - **name**: The axiom/postulate name
   - **statement**: What it asserts
   - **role**: How it functions in the paper's argument

3. **novel_terms**: Terminology introduced or coined by the authors.
   - **term**: The new term
   - **meaning**: What the authors mean by it
   - **motivation**: Why they introduce it (what gap it fills)

4. **nonstandard_usage**: Existing terms used in an unusual or field-specific way differing from their common meaning.
   - **term**: The term
   - **standard_meaning**: The common/standard meaning
   - **usage_here**: How this paper uses it differently

Return ONLY valid JSON. No markdown fences. No explanation.
{{
  "definitions": [{{"term": "...", "definition": "...", "section": "...", "formal": false}}],
  "axioms": [{{"name": "...", "statement": "...", "role": "..."}}],
  "novel_terms": [{{"term": "...", "meaning": "...", "motivation": "..."}}],
  "nonstandard_usage": [{{"term": "...", "standard_meaning": "...", "usage_here": "..."}}]
}}"""


def build_openq_prompt(ctx):
    """Prompt for open questions, limitations, and future work extraction."""
    return f"""You are extracting open questions and limitations from a scientific paper.

**Paper:** {ctx["paper_slug"]}
**Title:** {ctx["paper_title"]}

Extract:
1. **limitations**: Limitations the authors explicitly acknowledge.
   - **limitation**: What the limitation is
   - **impact**: How it affects the paper's conclusions
   - **stated_by_authors**: true if the authors state this, false if inferred

2. **open_problems**: Open problems or unresolved questions identified in the paper.
   - **problem**: The open question
   - **context**: Why it matters for this work
   - **tractability**: Authors' assessment if given: near_term, medium_term, long_term, unknown

3. **future_work**: Specific future work directions suggested by the authors.
   - **direction**: What they propose
   - **specificity**: How concrete: concrete, general, speculative

4. **tensions**: Unresolved tensions, apparent contradictions, or gaps between what the paper claims and what it demonstrates.
   - **tension**: Description of the tension
   - **between**: What two things are in tension

Return ONLY valid JSON. No markdown fences. No explanation.
{{
  "limitations": [{{"limitation": "...", "impact": "...", "stated_by_authors": true}}],
  "open_problems": [{{"problem": "...", "context": "...", "tractability": "unknown"}}],
  "future_work": [{{"direction": "...", "specificity": "concrete"}}],
  "tensions": [{{"tension": "...", "between": "..."}}]
}}"""


# ─────────────────────────────────────────────
# Output handlers
#
# Each returns a list of JSONL lines.
# ─────────────────────────────────────────────

def handle_metadata_output(extraction, ctx):
    """Create Paper update, Author nodes, Concept nodes, and edges."""
    lines = []
    if not extraction:
        return lines

    slug = ctx["paper_slug"]
    concepts = ctx["concepts"]
    authors = ctx["authors"]

    update_data = {
        "slug": slug, "title": ctx["paper_title"],
        "folder": ctx["paper_folder"], "added": ctx["paper_added"],
    }
    if extraction.get("year"):
        update_data["year"] = extraction["year"]
    if extraction.get("abstract"):
        update_data["abstract"] = extraction["abstract"]
    lines.append(json.dumps({"type": "Paper", "data": update_data}))

    for author in extraction.get("authors", []):
        name = author.get("name", "").strip()
        if not name:
            continue
        a_slug = make_author_slug(name)
        if a_slug not in authors:
            lines.append(json.dumps({"type": "Author", "data": {"slug": a_slug, "name": name}}))
            authors[a_slug] = {"slug": a_slug, "name": name}
        lines.append(json.dumps({"edge": "WrittenBy", "from": slug, "to": a_slug}))

    for concept in extraction.get("concepts", []):
        c_slug = concept.get("slug", "")
        c_name = concept.get("name", "")
        if not c_slug:
            c_slug = make_concept_slug(c_name) if c_name else ""
        if not c_slug:
            continue
        if c_slug not in concepts:
            lines.append(json.dumps({"type": "Concept", "data": {"slug": c_slug, "name": c_name or c_slug}}))
            concepts[c_slug] = {"slug": c_slug, "name": c_name or c_slug}
        lines.append(json.dumps({"edge": "Covers", "from": slug, "to": c_slug}))

    for cited in extraction.get("cites_in_collection", []):
        if cited and cited != slug:
            lines.append(json.dumps({"edge": "Cites", "from": slug, "to": cited}))

    n_a = len(extraction.get("authors", []))
    n_c = len(extraction.get("concepts", []))
    n_ci = len(extraction.get("cites_in_collection", []))
    print(f"  OK: {n_a} authors, {n_c} concepts, {n_ci} citations", file=sys.stderr)
    return lines


def handle_figures_output(extraction, ctx):
    """Create Figure nodes + HasFigure edges."""
    lines = []
    if not extraction or not extraction.get("figures"):
        return lines

    slug = ctx["paper_slug"]

    for i, fig in enumerate(extraction["figures"], 1):
        fig_id = fig.get("id", f"Figure {i}")
        fig_slug = f"{slug}--fig-{i}"

        key_data = fig.get("key_data", [])
        key_data_str = "; ".join(key_data) if isinstance(key_data, list) else str(key_data or "")

        node = {
            "type": "Figure",
            "data": {
                "slug": fig_slug,
                "figure_id": fig_id,
                "caption": fig.get("caption", ""),
                "figure_type": fig.get("type", "other"),
                "description": fig.get("description", ""),
                "key_data": key_data_str,
                "significance": fig.get("significance", ""),
            },
        }
        lines.append(json.dumps(node))
        lines.append(json.dumps({"edge": "HasFigure", "from": slug, "to": fig_slug}))

    print(f"  OK: {len(extraction['figures'])} figures/tables", file=sys.stderr)
    return lines


def handle_claims_output(extraction, ctx):
    """Update Paper.thesis, create Claim nodes + MakesClaim edges."""
    lines = []
    if not extraction:
        return lines

    slug = ctx["paper_slug"]

    if extraction.get("thesis") or extraction.get("structure"):
        paper_update = {
            "slug": slug, "title": ctx["paper_title"],
            "folder": ctx["paper_folder"], "added": ctx["paper_added"],
        }
        if extraction.get("thesis"):
            paper_update["thesis"] = extraction["thesis"]
        lines.append(json.dumps({"type": "Paper", "data": paper_update}))

    claim_n = 0
    for i, c in enumerate(extraction.get("claims", []), 1):
        claim_text = c.get("claim", "").strip()
        if not claim_text:
            continue
        claim_n += 1
        c_slug = f"{slug}--claim-{claim_n}"
        node = {
            "type": "Claim",
            "data": {
                "slug": c_slug,
                "claim": claim_text,
                "evidence_type": c.get("evidence_type", ""),
                "strength": c.get("strength", ""),
                "support": c.get("support", ""),
            },
        }
        lines.append(json.dumps(node))
        lines.append(json.dumps({"edge": "MakesClaim", "from": slug, "to": c_slug}))

    for assumption in extraction.get("assumptions", []):
        if not assumption or not assumption.strip():
            continue
        claim_n += 1
        a_slug = f"{slug}--claim-{claim_n}"
        node = {
            "type": "Claim",
            "data": {
                "slug": a_slug,
                "claim": assumption.strip(),
                "evidence_type": "assumption",
                "strength": "",
                "support": "",
            },
        }
        lines.append(json.dumps(node))
        lines.append(json.dumps({"edge": "MakesClaim", "from": slug, "to": a_slug}))

    print(f"  OK: {claim_n} claims/assumptions", file=sys.stderr)
    return lines


def handle_relations_output(extraction, ctx):
    """Create Extends / Contradicts edges."""
    lines = []
    if not extraction:
        return lines

    slug = ctx["paper_slug"]
    extends = extraction.get("extends", [])
    contradicts = extraction.get("contradicts", [])

    for rel in extends:
        r_slug = rel.get("slug", "")
        if r_slug:
            lines.append(json.dumps({"edge": "Extends", "from": slug, "to": r_slug}))

    for rel in contradicts:
        r_slug = rel.get("slug", "")
        if r_slug:
            lines.append(json.dumps({"edge": "Contradicts", "from": slug, "to": r_slug}))

    print(f"  OK: {len(extends)} extends, {len(contradicts)} contradicts", file=sys.stderr)
    return lines


def handle_methods_output(extraction, ctx):
    """Update Paper.study_type, create Technique nodes + UsesTechnique edges."""
    lines = []
    if not extraction:
        return lines

    slug = ctx["paper_slug"]
    techniques = ctx["techniques"]

    study_type = extraction.get("study_type")
    if study_type:
        if isinstance(study_type, list):
            study_type = ", ".join(study_type)
        paper_update = {
            "slug": slug, "title": ctx["paper_title"],
            "folder": ctx["paper_folder"], "added": ctx["paper_added"],
            "study_type": study_type,
        }
        lines.append(json.dumps({"type": "Paper", "data": paper_update}))

    tech_count = 0
    for t in extraction.get("techniques", []):
        t_slug = t.get("slug", "")
        t_name = t.get("name", "")
        if not t_slug:
            t_slug = make_technique_slug(t_name) if t_name else ""
        if not t_slug:
            continue
        tech_count += 1
        if t_slug not in techniques:
            node = {
                "type": "Technique",
                "data": {
                    "slug": t_slug,
                    "name": t_name or t_slug,
                    "category": t.get("category", "other"),
                },
            }
            lines.append(json.dumps(node))
            techniques[t_slug] = {"slug": t_slug, "name": t_name or t_slug}
        lines.append(json.dumps({"edge": "UsesTechnique", "from": slug, "to": t_slug}))

    print(f"  OK: study_type={study_type}, {tech_count} techniques", file=sys.stderr)
    return lines


def handle_definitions_output(extraction, ctx):
    """Create Definition nodes + HasDefinition edges."""
    lines = []
    if not extraction:
        return lines

    slug = ctx["paper_slug"]
    n = 0

    for d in extraction.get("definitions", []):
        term = d.get("term", "").strip()
        defn = d.get("definition", "").strip()
        if not term or not defn:
            continue
        n += 1
        term_slug = make_concept_slug(term)
        d_slug = f"{slug}--def-{term_slug}"
        node = {
            "type": "Definition",
            "data": {
                "slug": d_slug,
                "term": term,
                "definition": defn,
                "section": d.get("section", ""),
                "formal": "true" if d.get("formal") else "false",
            },
        }
        lines.append(json.dumps(node))
        lines.append(json.dumps({"edge": "HasDefinition", "from": slug, "to": d_slug}))

    for ax in extraction.get("axioms", []):
        name = ax.get("name", "").strip()
        statement = ax.get("statement", "").strip()
        if not name or not statement:
            continue
        n += 1
        ax_slug_part = make_concept_slug(name)
        ax_slug = f"{slug}--def-{ax_slug_part}"
        node = {
            "type": "Definition",
            "data": {
                "slug": ax_slug,
                "term": name,
                "definition": statement,
                "section": "",
                "formal": "true",
            },
        }
        lines.append(json.dumps(node))
        lines.append(json.dumps({"edge": "HasDefinition", "from": slug, "to": ax_slug}))

    for nt in extraction.get("novel_terms", []):
        term = nt.get("term", "").strip()
        meaning = nt.get("meaning", "").strip()
        if not term or not meaning:
            continue
        n += 1
        nt_slug_part = make_concept_slug(term)
        nt_slug = f"{slug}--def-{nt_slug_part}"
        node = {
            "type": "Definition",
            "data": {
                "slug": nt_slug,
                "term": term,
                "definition": meaning,
                "section": "",
                "formal": "false",
            },
        }
        lines.append(json.dumps(node))
        lines.append(json.dumps({"edge": "HasDefinition", "from": slug, "to": nt_slug}))

    for ns in extraction.get("nonstandard_usage", []):
        term = ns.get("term", "").strip()
        usage = ns.get("usage_here", "").strip()
        if not term or not usage:
            continue
        n += 1
        ns_slug_part = make_concept_slug(term)
        ns_slug = f"{slug}--def-ns-{ns_slug_part}"
        node = {
            "type": "Definition",
            "data": {
                "slug": ns_slug,
                "term": term,
                "definition": usage,
                "section": "",
                "formal": "false",
            },
        }
        lines.append(json.dumps(node))
        lines.append(json.dumps({"edge": "HasDefinition", "from": slug, "to": ns_slug}))

    print(f"  OK: {n} definitions/axioms/terms", file=sys.stderr)
    return lines


def handle_openq_output(extraction, ctx):
    """Create OpenQuestion nodes + Raises edges."""
    lines = []
    if not extraction:
        return lines

    slug = ctx["paper_slug"]
    n = 0

    for lim in extraction.get("limitations", []):
        text = lim.get("limitation", "").strip()
        if not text:
            continue
        n += 1
        q_slug = f"{slug}--oq-{n}"
        node = {
            "type": "OpenQuestion",
            "data": {
                "slug": q_slug,
                "question": text,
                "context": lim.get("impact", ""),
                "tractability": "",
                "question_type": "limitation",
            },
        }
        lines.append(json.dumps(node))
        lines.append(json.dumps({"edge": "Raises", "from": slug, "to": q_slug}))

    for prob in extraction.get("open_problems", []):
        text = prob.get("problem", "").strip()
        if not text:
            continue
        n += 1
        q_slug = f"{slug}--oq-{n}"
        node = {
            "type": "OpenQuestion",
            "data": {
                "slug": q_slug,
                "question": text,
                "context": prob.get("context", ""),
                "tractability": prob.get("tractability", "unknown"),
                "question_type": "open_problem",
            },
        }
        lines.append(json.dumps(node))
        lines.append(json.dumps({"edge": "Raises", "from": slug, "to": q_slug}))

    for fw in extraction.get("future_work", []):
        text = fw.get("direction", "").strip()
        if not text:
            continue
        n += 1
        q_slug = f"{slug}--oq-{n}"
        node = {
            "type": "OpenQuestion",
            "data": {
                "slug": q_slug,
                "question": text,
                "context": "",
                "tractability": fw.get("specificity", "general"),
                "question_type": "future_work",
            },
        }
        lines.append(json.dumps(node))
        lines.append(json.dumps({"edge": "Raises", "from": slug, "to": q_slug}))

    for t in extraction.get("tensions", []):
        text = t.get("tension", "").strip()
        if not text:
            continue
        n += 1
        q_slug = f"{slug}--oq-{n}"
        node = {
            "type": "OpenQuestion",
            "data": {
                "slug": q_slug,
                "question": text,
                "context": t.get("between", ""),
                "tractability": "",
                "question_type": "tension",
            },
        }
        lines.append(json.dumps(node))
        lines.append(json.dumps({"edge": "Raises", "from": slug, "to": q_slug}))

    print(f"  OK: {n} open questions", file=sys.stderr)
    return lines


# ─────────────────────────────────────────────
# Mode registry
# ─────────────────────────────────────────────

MODES = {
    "metadata": {
        "build_prompt": build_metadata_prompt,
        "handle_output": handle_metadata_output,
        "max_tokens": 8192,
    },
    "figures": {
        "build_prompt": build_figures_prompt,
        "handle_output": handle_figures_output,
        "max_tokens": 16384,
    },
    "claims": {
        "build_prompt": build_claims_prompt,
        "handle_output": handle_claims_output,
        "max_tokens": 8192,
    },
    "relations": {
        "build_prompt": build_relations_prompt,
        "handle_output": handle_relations_output,
        "max_tokens": 8192,
    },
    "methods": {
        "build_prompt": build_methods_prompt,
        "handle_output": handle_methods_output,
        "max_tokens": 8192,
    },
    "definitions": {
        "build_prompt": build_definitions_prompt,
        "handle_output": handle_definitions_output,
        "max_tokens": 8192,
    },
    "open-questions": {
        "build_prompt": build_openq_prompt,
        "handle_output": handle_openq_output,
        "max_tokens": 8192,
    },
}


# ─────────────────────────────────────────────
# Core processing
# ─────────────────────────────────────────────

def process_paper(pdf_path, mode_name, ctx):
    """Process a single paper with the given mode. Returns JSONL lines."""
    mode = MODES[mode_name]
    paper_slug = Path(pdf_path).stem
    paper_data = ctx["papers"].get(paper_slug, {})

    paper_ctx = {
        **ctx,
        "paper_slug": paper_slug,
        "paper_title": paper_data.get("title", paper_slug),
        "paper_folder": paper_data.get("folder", ""),
        "paper_added": paper_data.get("added", ""),
    }

    print(f"  Extracting ({mode_name}): {paper_slug}", file=sys.stderr)

    prompt = mode["build_prompt"](paper_ctx)
    extraction = call_gemini(str(pdf_path), prompt, max_tokens=mode["max_tokens"])

    if not extraction:
        print(f"  FAILED: {paper_slug}", file=sys.stderr)
        return []

    return mode["handle_output"](extraction, paper_ctx)


def parse_args(args):
    """Parse CLI arguments, returning (flags, mode_name, pdf_paths)."""
    flags = set()
    mode_name = "metadata"
    pdf_paths = []

    i = 0
    while i < len(args):
        if args[i] == "--mode":
            if i + 1 < len(args):
                mode_name = args[i + 1]
                i += 2
            else:
                print("Error: --mode requires a value", file=sys.stderr)
                sys.exit(1)
        elif args[i].startswith("--"):
            flags.add(args[i])
            i += 1
        else:
            pdf_paths.append(args[i])
            i += 1

    return flags, mode_name, pdf_paths


def main():
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    flags, mode_name, pdf_args = parse_args(args)
    append_mode = "--append" in flags
    all_mode = "--all" in flags
    dry_run = "--dry-run" in flags

    if mode_name not in MODES:
        print(f"Error: unknown mode '{mode_name}'. Available: {', '.join(MODES)}", file=sys.stderr)
        sys.exit(1)

    papers, concepts, authors, techniques, enriched = load_seed_data()
    ctx = {"papers": papers, "concepts": concepts, "authors": authors, "techniques": techniques}

    all_lines = []

    if all_mode:
        edge_type = MODE_EDGE[mode_name]
        already_done = enriched.get(edge_type, set())
        # For relations, also count Contradicts
        if mode_name == "relations":
            already_done = already_done | enriched.get("Contradicts", set())
        candidates = [s for s in papers if s not in already_done]

        total = len(candidates)
        print(f"Found {total} papers to process ({mode_name} mode, {len(papers)} total)", file=sys.stderr)

        if dry_run:
            for slug in candidates:
                print(f"  Would extract ({mode_name}): {slug}")
            sys.exit(0)

        for i, slug in enumerate(candidates):
            pdf_path = find_pdf_path(slug, papers)
            if not pdf_path:
                print(f"  SKIP (no PDF): {slug}", file=sys.stderr)
                continue

            print(f"[{i+1}/{total}]", file=sys.stderr)
            lines = process_paper(pdf_path, mode_name, ctx)

            if append_mode and lines:
                with open(SEED_FILE, "a") as f:
                    for line in lines:
                        f.write(line + "\n")
            else:
                all_lines.extend(lines)

            if i < total - 1:
                time.sleep(REQUEST_DELAY_S)
    else:
        for pdf_arg in pdf_args:
            pdf_path = Path(pdf_arg).resolve()
            if not pdf_path.exists():
                print(f"Error: {pdf_path} not found", file=sys.stderr)
                continue

            if dry_run:
                paper_slug = pdf_path.stem
                print(f"Would extract ({mode_name}): {paper_slug}")
                print(f"  File: {pdf_path}")
                print(f"  Size: {pdf_path.stat().st_size / (1024*1024):.1f}MB")
                continue

            lines = process_paper(pdf_path, mode_name, ctx)
            all_lines.extend(lines)

    if dry_run:
        sys.exit(0)

    if all_lines:
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
