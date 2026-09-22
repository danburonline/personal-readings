---
name: nanograph
description: Discover papers and cross-paper relationships in the Readings library, verify extraction provenance, and maintain its Nanograph records. Use for literature discovery, adding papers or authorised graph enrichment in this repository.
---

# Nanograph -- Readings Knowledge Graph

This research library includes a [nanograph](https://github.com/nanograph/nanograph) property graph at the repository root. Use nanograph v1.3 or later.

## Retrieval

Start with the repository's `AGENTS.md`. Query the graph for relevant papers and relationships, use `paperDetails` for the PDF path and `extractionsByPaper` for provenance, then read the source PDF and cite the page or section. Scientific claims remain grounded in the source, not an unreviewed extraction. Missing relationships do not prove absence; fall back to file search where coverage is incomplete. Read-only retrieval does not authorise extraction, ingestion or API calls. This skill belongs to this repository, not every workspace containing research.

## Files

| File                    | Purpose                                                       |
| ----------------------- | ------------------------------------------------------------- |
| `_graph/readings.pg`    | Schema definition                                             |
| `_graph/readings.gq`    | Named queries                                                 |
| `_graph/seed.jsonl`     | All graph data (nodes + edges)                                |
| `_graph/extract.py`     | Multi-mode Gemini extraction script (all modes produce JSONL) |
| `_graph/build_seed.py`  | Canonicalise seed.jsonl (union Paper fields, dedupe nodes/edges) |
| `_graph/rebuild.py`     | Staged validation and explicit activation with an unused backup |
| `_graph/readings.nano/` | Compiled database (gitignored, rebuilt from schema + data)    |

## Schema

**Nodes:** Paper, Author, Concept, TopicFolder, Figure, Claim, Technique, Definition, OpenQuestion, Extraction
**Edges:** Cites, Extends, Contradicts, WrittenBy, Covers, InFolder, AffiliatedWith, HasFigure, MakesClaim, UsesTechnique, HasDefinition, Raises, HasExtraction

Every node type has a `slug: String @key` used for edge references.

Paper has: `slug` (frozen identity), `title`, `folder`, `added` (YYYYMMDD), plus optional `filename`, `path`, `year`, `abstract`, `thesis`, `study_type`, `doi`, `arxiv_id`. Renaming a PDF updates `filename`, `path`, `folder`, and InFolder -- it does not change `slug` or edge endpoints. Child slugs (`{slug}--fig-1`, `{slug}--metadata--{run_id}`, and legacy `{slug}--metadata`) stay keyed off the frozen slug.

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
{"type": "Extraction", "data": {"slug": "20260115_my_paper--metadata--unique_run_id", "mode": "metadata", "model": "gemini-3.7-flash", "timestamp": "2026-08-26T12:00:00Z", "pdf_checksum": "...", "version": "1.2.0", "result_status": "ok", "review_status": "unreviewed"}}
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
{"edge": "HasExtraction", "from": "20260115_my_paper", "to": "20260115_my_paper--metadata--unique_run_id"}
```

**Critical:** Edges use `"edge"` key, NOT `"type"`. The `"from"` and `"to"` values must match existing `@key` slugs.

## CLI Commands

Run the examples from the repository root. There is no `nanograph.toml`; direct commands need explicit database, schema and query paths. For a fresh checkout, schema change or record removal, follow [Graph maintenance](../../../README.md#graph-maintenance): validate a separate build, stop database clients and seed writers before activation, and retain the previous database as a backup. Never merge backup database contents into the seed.

Use one seed writer at a time, including manual editors, before any append, canonicalisation or rebuild. The three helpers share an advisory `seed.jsonl.write-lock` and refuse contention; extraction holds it throughout an append run. Editors and direct Nanograph commands do not honour that lock. Change checks reject intervening seed edits but do not make arbitrary simultaneous writes safe. On contention, wait for the owner to finish. Remove an abandoned empty lock only after establishing that its process has stopped; see the maintenance reference above.

```bash
# Build and validate without changing the active database
python3 _graph/rebuild.py

# First setup, or activate a fresh build with an unused backup
python3 _graph/rebuild.py --activate

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

| Query                      | Params       | Returns                                          |
| -------------------------- | ------------ | ------------------------------------------------ |
| `allPapers`                | --           | Full catalogue by date                           |
| `allFolders`               | --           | Topic folders                                    |
| `papersPerFolder`          | --           | Paper counts per folder                          |
| `paperDetails`             | `paper`      | All stored fields for one paper, including path  |
| `papersByFolder`           | `folder`     | Papers in a topic dir                            |
| `papersByConcept`          | `concept`    | Papers covering a concept                        |
| `papersByAuthor`           | `author`     | Papers by an author                              |
| `papersByTechnique`        | `technique`  | Papers using a technique                         |
| `citedBy`                  | `paper`      | Papers citing a paper                            |
| `citesWhat`                | `paper`      | Papers a paper cites                             |
| `extendsWhat`              | `paper`      | Papers a paper extends                           |
| `extendedBy`               | `paper`      | Papers that extend a paper                       |
| `contradictsWhat`          | `paper`      | Papers a paper contradicts                       |
| `contradictedBy`           | `paper`      | Papers that contradict a paper                   |
| `extendsPerPaper`          | --           | Extends counts, highest degree first             |
| `contradictsPerPaper`      | --           | Contradicts counts, highest degree first         |
| `techniquesByPaper`        | `paper`      | Techniques used by a paper                       |
| `definitionsByTerm`        | `term`       | All definitions of a term across papers          |
| `definitionsByPaper`       | `paper`      | Definitions from a paper                         |
| `figuresByPaper`           | `paper`      | Figures in a paper                               |
| `claimsByPaper`            | `paper`      | Claims made by a paper                           |
| `openQuestionsByPaper`     | `paper`      | Open questions from a paper                      |
| `extractionsByPaper`       | `paper`      | Extraction provenance for a paper                |
| `papersMissingMetadata`    | --           | Papers with no WrittenBy edge                    |
| `papersMissingFigures`     | --           | Papers with no HasFigure edge                    |
| `papersMissingClaims`      | --           | Papers with no MakesClaim edge                   |
| `papersMissingRelations`   | --           | Papers with no Extends and no Contradicts        |
| `papersMissingMethods`     | --           | Papers with no UsesTechnique edge                |
| `papersMissingDefinitions` | --           | Papers with no HasDefinition edge                |
| `papersMissingQuestions`   | --           | Papers with no Raises edge                       |

The `papersMissing*` queries measure missing output edges, not extraction attempts. A valid empty result still counts as a successful attempt. Inspect `extractionsByPaper` for `result_status` and `review_status`; success is not scientific review.

## Workflows

### Adding a new paper

1. Append Paper node + InFolder edge to `_graph/seed.jsonl` (do **not** reload yet if extraction modes will follow)
2. Run all desired extraction modes with `--append` (see below)
3. Canonicalise: `python3 _graph/build_seed.py --write` -- see "Duplicate Paper nodes" below
4. Then reload: `nanograph load --db _graph/readings.nano --data _graph/seed.jsonl --mode merge`

Keep exactly one Paper node per slug in `seed.jsonl`.

### Enriching after reading

After extracting knowledge from a paper, append to `_graph/seed.jsonl`:

- Author nodes + WrittenBy edges
- Concept nodes + Covers edges
- Cites / Extends / Contradicts edges to other papers **in this collection**

Then reload with `--mode merge`.

### Automated extraction with Gemini

The repository includes `_graph/extract.py` -- a multi-mode extraction script that uses the Gemini model selected by `GEMINI_MODEL` (default `gemini-3.7-flash`). Every mode produces JSONL for the knowledge graph.

**Prerequisites:**

- `GEMINI_API_KEY` environment variable must be set
- `GEMINI_MODEL` is optional and defaults to `gemini-3.7-flash`
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

Every handled mode run also emits a unique Extraction node (`{paper_slug}--{mode}--{run_id}`) and a HasExtraction edge, including skipped and failed runs. Mode-specific structural checks require explicit collections with valid field types; genuine empty collections are allowed. A handled model or output-processing failure discards its proposed output and cache changes, emits failed provenance and continues the batch. Abrupt termination or filesystem failure can prevent persistence. `EXTRACTION_VERSION` in `extract.py` is the short version string stored on that node. Existing legacy per-mode records remain valid and unchanged; new retries preserve both failure and success history.

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

**Deduplication / crash recovery:** For `--all`, each mode checks `seed.jsonl` for its marker edge type (e.g. `HasFigure` for figures mode, `WrittenBy` for metadata) and for a linked Extraction with `result_status=ok`. Papers with the relevant edge or any successful attempt are skipped, including successful empty results. This is not a checksum freshness or review check; use a named paper for an authorised retry. In `--all --append` mode, JSONL is flushed after each paper; inspect the last records after an interrupted write before resuming. Technique nodes (like Author and Concept) are deduplicated in memory during a run.

**After extraction:**

```bash
python3 _graph/build_seed.py --write
nanograph load --db _graph/readings.nano --data _graph/seed.jsonl --mode merge
```

**Duplicate nodes and corrections:** `metadata`, `claims`, and `methods` append partial Paper nodes. Nanograph rejects duplicate keys in one load. Inspect `python3 _graph/build_seed.py`, then use `--write` to fill missing fields and deduplicate records. Conflicting non-empty values block writing, including old duplicate Extraction statuses; neither first-write-wins nor last-write-wins is a correction policy. Follow [Corrections and repeated extraction](../../../README.md#corrections-and-repeated-extraction) to resolve source-backed corrections explicitly. Review re-extraction output without `--append` before ingestion where assertions already exist. A new successful attempt does not replace curated claims or alter historical provenance.

**Limitations:**

- PDFs >35MB are skipped (`MAX_PDF_SIZE_MB` in `extract.py`; Gemini inline data limit)
- Some papers may fail due to JSON truncation (retry individually if needed)
- Citations and relations are only detected against papers already in the collection

## Conventions

- Paper slugs: frozen identity, usually the original lowercase `snake_case` PDF stem (e.g. `20250703_neurophenomenal_structuralism`). Renames update `filename` and `path`, not `slug`
- Author slugs: `lastname-firstname` lowercase (e.g. `tononi-giulio`)
- Concept slugs: lowercase hyphenated (e.g. `integrated-information-theory`)
- Technique slugs: lowercase hyphenated (e.g. `calcium-imaging`, `patch-clamp-electrophysiology`)
- Figure slugs: `{paper_slug}--fig-{n}` (e.g. `20260115_my_paper--fig-1`)
- Claim slugs: `{paper_slug}--claim-{n}`
- Definition slugs: `{paper_slug}--def-{term_slug}` (e.g. `20260115_my_paper--def-consciousness`)
- OpenQuestion slugs: `{paper_slug}--oq-{n}`
- Extraction slugs: new attempts use `{paper_slug}--{mode}--{run_id}`; legacy `{paper_slug}--{mode}` records remain valid. Follow HasExtraction edges instead of parsing slugs

Always check existing slugs before creating duplicates: `nanograph run --db _graph/readings.nano --query _graph/readings.gq --name allPapers`

Append routine enrichment to `_graph/seed.jsonl`. Authorised source-backed corrections and controlled canonicalisation are the documented exceptions. The seed is the source of truth for graph records; PDFs remain the evidence for scientific claims.
