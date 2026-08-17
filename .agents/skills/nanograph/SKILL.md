---
name: nanograph
description: Manage the Readings knowledge graph -- add papers, enrich with authors/concepts/citations, query cross-topic relationships. Use when adding papers, extracting knowledge, or querying the research library graph.
---

# Nanograph -- Readings Knowledge Graph

This research library includes a [nanograph](https://github.com/nanograph/nanograph) property graph at the repository root. Use nanograph v1.3 or later.

## Files

| File                    | Purpose                                                       |
| ----------------------- | ------------------------------------------------------------- |
| `_graph/readings.pg`    | Schema definition                                             |
| `_graph/readings.gq`    | Named queries                                                 |
| `_graph/seed.jsonl`     | All graph data (nodes + edges)                                |
| `_graph/extract.py`     | Multi-mode Gemini extraction script (all modes produce JSONL) |
| `_graph/readings.nano/` | Compiled database (gitignored, rebuilt from schema + data)    |

## Schema

**Nodes:** Paper, Author, Concept, TopicFolder, Manuscript, Figure, Claim, Technique, Definition, OpenQuestion
**Edges:** Cites, Extends, Contradicts, WrittenBy, Covers, InFolder, Informs, AffiliatedWith, HasFigure, MakesClaim, UsesTechnique, HasDefinition, Raises

Every node type has a `slug: String @key` used for edge references.

Paper has: `slug`, `title`, `folder`, `added` (YYYYMMDD), plus optional `year`, `abstract`, `thesis`, `study_type`, `doi`, `arxiv_id`.

## JSONL Format

Nodes:

```json
{"type": "Paper", "data": {"slug": "20260115_my_paper", "title": "My paper", "folder": "consciousness_theories", "added": "20260115"}}
{"type": "Author", "data": {"slug": "tononi-giulio", "name": "Giulio Tononi"}}
{"type": "Concept", "data": {"slug": "iit", "name": "Integrated Information Theory"}}
{"type": "Technique", "data": {"slug": "calcium-imaging", "name": "Calcium Imaging", "category": "imaging"}}
{"type": "Figure", "data": {"slug": "20260115_my_paper--fig-1", "figure_id": "Figure 1", "caption": "...", "figure_type": "diagram", "description": "...", "key_data": "...", "significance": "..."}}
{"type": "Claim", "data": {"slug": "20260115_my_paper--claim-1", "claim": "...", "evidence_type": "empirical", "strength": "strong", "support": "..."}}
{"type": "Definition", "data": {"slug": "20260115_my_paper--def-consciousness", "term": "consciousness", "definition": "...", "section": "2.1", "formal": "false"}}
{"type": "OpenQuestion", "data": {"slug": "20260115_my_paper--oq-1", "question": "...", "context": "...", "tractability": "near_term", "question_type": "open_problem"}}
```

Edges:

```json
{"edge": "WrittenBy", "from": "20260115_my_paper", "to": "tononi-giulio"}
{"edge": "Covers", "from": "20260115_my_paper", "to": "iit"}
{"edge": "Cites", "from": "20260115_my_paper", "to": "20250930_other_paper"}
{"edge": "HasFigure", "from": "20260115_my_paper", "to": "20260115_my_paper--fig-1"}
{"edge": "MakesClaim", "from": "20260115_my_paper", "to": "20260115_my_paper--claim-1"}
{"edge": "UsesTechnique", "from": "20260115_my_paper", "to": "calcium-imaging"}
{"edge": "HasDefinition", "from": "20260115_my_paper", "to": "20260115_my_paper--def-consciousness"}
{"edge": "Raises", "from": "20260115_my_paper", "to": "20260115_my_paper--oq-1"}
```

**Critical:** Edges use `"edge"` key, NOT `"type"`. The `"from"` and `"to"` values must match existing `@key` slugs.

## CLI Commands

The active database was rebuilt with nanograph 1.3.0 on 17 August 2026 and passes `lint` and `doctor`. `_graph/readings.nano.legacy-v3/` is a stale rollback artefact and must never be merged into the active graph. This repository intentionally has no `nanograph.toml`; always pass explicit database, schema, and query paths. Remove any configuration scaffold generated under `_graph/` during a staged rebuild.

```bash
# Future complete rebuild through a staging database
nanograph init --db _graph/readings.nano.new --schema _graph/readings.pg
nanograph load --db _graph/readings.nano.new --data _graph/seed.jsonl --mode overwrite
nanograph lint --db _graph/readings.nano.new --query _graph/readings.gq
nanograph doctor --db _graph/readings.nano.new --schema _graph/readings.pg --verbose

# Incremental update (after appending to seed.jsonl)
nanograph load --db _graph/readings.nano --data _graph/seed.jsonl --mode merge

# Run a named query
nanograph run --db _graph/readings.nano --query _graph/readings.gq --name <query_name>
nanograph run --db _graph/readings.nano --query _graph/readings.gq --name papersByFolder --param folder=consciousness_theories

# Inspect
nanograph describe --db _graph/readings.nano
nanograph lint --db _graph/readings.nano --query _graph/readings.gq
nanograph doctor --db _graph/readings.nano --schema _graph/readings.pg --verbose
```

## Available Queries

| Query                  | Params       | Returns                                 |
| ---------------------- | ------------ | --------------------------------------- |
| `allPapers`            | --           | Full catalogue by date                  |
| `allFolders`           | --           | Topic folders                           |
| `papersPerFolder`      | --           | Paper counts per folder                 |
| `allManuscripts`       | --           | Daniel's manuscripts + status           |
| `papersByFolder`       | `folder`     | Papers in a topic dir                   |
| `papersByConcept`      | `concept`    | Papers covering a concept               |
| `papersByAuthor`       | `author`     | Papers by an author                     |
| `papersByTechnique`    | `technique`  | Papers using a technique                |
| `citedBy`              | `paper`      | Papers citing a paper                   |
| `citesWhat`            | `paper`      | Papers a paper cites                    |
| `papersForManuscript`  | `manuscript` | Papers informing a manuscript           |
| `techniquesByPaper`    | `paper`      | Techniques used by a paper              |
| `definitionsByTerm`    | `term`       | All definitions of a term across papers |
| `definitionsByPaper`   | `paper`      | Definitions from a paper                |
| `figuresByPaper`       | `paper`      | Figures in a paper                      |
| `claimsByPaper`        | `paper`      | Claims made by a paper                  |
| `openQuestionsByPaper` | `paper`      | Open questions from a paper             |

## Workflows

### Adding a new paper

1. Append Paper node + InFolder edge to `_graph/seed.jsonl` (do **not** reload yet if extraction modes will follow)
2. Run all desired extraction modes with `--append` (see below)
3. Squash the duplicate Paper nodes for the new slug into a single node (union of all fields) -- see "Duplicate Paper nodes" below
4. Then reload: `nanograph load --db _graph/readings.nano --data _graph/seed.jsonl --mode merge`

Keep exactly one Paper node per slug in `seed.jsonl`.

### Enriching after reading

After extracting knowledge from a paper, append to `_graph/seed.jsonl`:

- Author nodes + WrittenBy edges
- Concept nodes + Covers edges
- Cites / Extends / Contradicts edges to other papers **in this collection**
- Informs edges to relevant manuscripts

Then reload with `--mode merge`.

### Automated extraction with Gemini

The repository includes `_graph/extract.py` -- a multi-mode extraction script that uses the Gemini model selected by `GEMINI_MODEL` (default `gemini-3.6-flash`). Every mode produces JSONL for the knowledge graph.

**Prerequisites:**

- `GEMINI_API_KEY` environment variable must be set
- `GEMINI_MODEL` is optional and defaults to `gemini-3.6-flash`
- No pip dependencies (stdlib only)

**Extraction modes:**

| Mode             | Graph output                                                                   |
| ---------------- | ------------------------------------------------------------------------------ |
| `metadata`       | Paper (year, abstract), Author, Concept nodes + WrittenBy, Covers, Cites edges |
| `figures`        | Figure nodes + HasFigure edges                                                 |
| `claims`         | Paper.thesis + Claim nodes + MakesClaim edges                                  |
| `relations`      | Extends / Contradicts edges                                                    |
| `methods`        | Paper.study_type + Technique nodes + UsesTechnique edges                       |
| `definitions`    | Definition nodes + HasDefinition edges                                         |
| `open-questions` | OpenQuestion nodes + Raises edges                                              |

**Usage:**

```bash
# Metadata extraction (default) -- prints JSONL to stdout
python3 _graph/extract.py path/to/paper.pdf

# Append JSONL directly to seed.jsonl
python3 _graph/extract.py path/to/paper.pdf --append

# Specialised extraction modes
python3 _graph/extract.py path/to/paper.pdf --mode figures --append
python3 _graph/extract.py path/to/paper.pdf --mode claims --append
python3 _graph/extract.py path/to/paper.pdf --mode relations --append
python3 _graph/extract.py path/to/paper.pdf --mode methods --append
python3 _graph/extract.py path/to/paper.pdf --mode definitions --append
python3 _graph/extract.py path/to/paper.pdf --mode open-questions --append

# Batch: all un-processed papers for a given mode
python3 _graph/extract.py --all --append
python3 _graph/extract.py --all --mode figures --append
python3 _graph/extract.py --all --mode relations --append

# Dry run (preview, no API call)
python3 _graph/extract.py --all --mode claims --dry-run
```

**Deduplication / crash recovery:** For `--all`, each mode checks `seed.jsonl` for its marker edge type (e.g. `HasFigure` for figures mode, `WrittenBy` for metadata). Papers that already have the relevant edge are skipped. In `--all --append` mode, JSONL is flushed to `seed.jsonl` after each paper, so a crash mid-batch loses at most the paper being processed -- re-running picks up where it left off. Technique nodes (like Author and Concept) are deduplicated in memory during a run.

**After extraction:**

```bash
nanograph load --db _graph/readings.nano --data _graph/seed.jsonl --mode merge
```

**Duplicate Paper nodes (merge gotcha):** `metadata`, `claims`, and `methods` each append their own Paper node for the processed slug (carrying `abstract`, `thesis`, and `study_type` respectively). nanograph rejects duplicate `@key` values within a single load, so if several modes ran for the same paper, squash those nodes into one node per slug (union of all fields, e.g. `year`, `doi`, `arxiv_id`, `abstract`, `thesis`, `study_type`) before reloading. Rewriting the file for a controlled migration or this squash is the exception to "never overwrite `seed.jsonl`".

**Limitations:**

- PDFs >35MB are skipped (`MAX_PDF_SIZE_MB` in `extract.py`; Gemini inline data limit)
- Some papers may fail due to JSON truncation (retry individually if needed)
- Citations and relations are only detected against papers already in the collection

### Manuscripts

Daniel's active manuscripts (use these slugs for Informs edges):

- `05-ocm` -- Operational Consciousness Mechanics
- `frontiers-consciousness-engineering` -- Synconetics Frontiers Paper
- `cortical-reorganisation` -- Glioma-Induced Cortical Reorganisation
- `hybrid-mind-uploading` -- Hybrid Mind Uploading

## Conventions

- Paper slugs: PDF filename minus `.pdf` extension (e.g. `20250703_neurophenomenal_structuralism`)
- Author slugs: `lastname-firstname` lowercase (e.g. `tononi-giulio`)
- Concept slugs: lowercase hyphenated (e.g. `integrated-information-theory`)
- Technique slugs: lowercase hyphenated (e.g. `calcium-imaging`, `patch-clamp-electrophysiology`)
- Figure slugs: `{paper_slug}--fig-{n}` (e.g. `20260115_my_paper--fig-1`)
- Claim slugs: `{paper_slug}--claim-{n}`
- Definition slugs: `{paper_slug}--def-{term_slug}` (e.g. `20260115_my_paper--def-consciousness`)
- OpenQuestion slugs: `{paper_slug}--oq-{n}`

Always check existing slugs before creating duplicates: `nanograph run --db _graph/readings.nano --query _graph/readings.gq --name allPapers`

Append to `_graph/seed.jsonl` -- never overwrite it. The file is the source of truth.
