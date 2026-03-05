---
name: nanograph
description: Manage the Readings knowledge graph -- add papers, enrich with authors/concepts/citations, query cross-topic relationships. Use when adding papers, extracting knowledge, or querying the research library graph.
---

# Nanograph -- Readings Knowledge Graph

This research library includes a [nanograph](https://github.com/aaltshuler/nanograph) property graph at the repository root.

## Files

| File | Purpose |
|---|---|
| `readings.pg` | Schema definition |
| `readings.gq` | Named queries |
| `seed.jsonl` | All graph data (nodes + edges) |
| `readings.nano/` | Compiled database (gitignored, rebuilt from schema + data) |

## Schema

**Nodes:** Paper, Author, Concept, TopicFolder, Manuscript
**Edges:** Cites, Extends, Contradicts, WrittenBy, Covers, InFolder, Informs, AffiliatedWith

Every Paper has: `slug` (@key, filename without .pdf), `title`, `folder`, `added` (YYYYMMDD).
Every node type has a `slug: String @key` used for edge references.

## JSONL Format

Nodes:
```json
{"type": "Paper", "data": {"slug": "20260115_my_paper_pdf", "title": "My paper", "folder": "consciousness_theories", "added": "20260115"}}
{"type": "Author", "data": {"slug": "tononi-giulio", "name": "Giulio Tononi"}}
{"type": "Concept", "data": {"slug": "iit", "name": "Integrated Information Theory", "description": "Mathematical theory identifying consciousness with integrated information"}}
```

Edges:
```json
{"edge": "InFolder", "from": "20260115_my_paper_pdf", "to": "consciousness_theories"}
{"edge": "WrittenBy", "from": "20260115_my_paper_pdf", "to": "tononi-giulio"}
{"edge": "Covers", "from": "20260115_my_paper_pdf", "to": "iit"}
{"edge": "Cites", "from": "20260115_my_paper_pdf", "to": "20250930_other_paper_pdf"}
{"edge": "Informs", "from": "20260115_my_paper_pdf", "to": "05-ocm"}
```

**Critical:** Edges use `"edge"` key, NOT `"type"`. The `"from"` and `"to"` values must match existing `@key` slugs.

## CLI Commands

```bash
# Rebuild from scratch
nanograph init readings.nano --schema readings.pg
nanograph load readings.nano --data seed.jsonl --mode overwrite

# Incremental update (after appending to seed.jsonl)
nanograph load readings.nano --data seed.jsonl --mode merge

# Run a named query
nanograph run --db readings.nano --query readings.gq --name <query_name>
nanograph run --db readings.nano --query readings.gq --name papersByFolder --param folder=consciousness_theories

# Inspect
nanograph describe --db readings.nano
nanograph check --db readings.nano --query readings.gq
nanograph doctor readings.nano
```

## Available Queries

| Query | Params | Returns |
|---|---|---|
| `allPapers` | -- | Full catalogue by date |
| `allFolders` | -- | Topic folders |
| `papersPerFolder` | -- | Paper counts per folder |
| `allManuscripts` | -- | Daniel's manuscripts + status |
| `papersByFolder` | `folder` | Papers in a topic dir |
| `papersByConcept` | `concept` | Papers covering a concept |
| `papersByAuthor` | `author` | Papers by an author |
| `citedBy` | `paper` | Papers citing a paper |
| `citesWhat` | `paper` | Papers a paper cites |
| `papersForManuscript` | `manuscript` | Papers informing a manuscript |

## Workflows

### Adding a new paper

1. Append Paper node + InFolder edge to `seed.jsonl`
2. Run: `nanograph load readings.nano --data seed.jsonl --mode merge`

### Enriching after reading

After extracting knowledge from a paper, append to `seed.jsonl`:
- Author nodes + WrittenBy edges
- Concept nodes + Covers edges
- Cites / Extends / Contradicts edges to other papers **in this collection**
- Informs edges to relevant manuscripts

Then reload with `--mode merge`.

### Manuscripts

Daniel's active manuscripts (use these slugs for Informs edges):
- `05-ocm` -- Operational Consciousness Mechanics
- `frontiers-consciousness-engineering` -- Synconetics Frontiers Paper
- `cortical-reorganisation` -- Glioma-Induced Cortical Reorganisation
- `hybrid-mind-uploading` -- Hybrid Mind Uploading

## Conventions

- Slugs use the PDF filename minus `.pdf` extension (e.g. `20250703_neurophenomenal_structuralism_pdf`)
- Author slugs: `lastname-firstname` lowercase (e.g. `tononi-giulio`)
- Concept slugs: lowercase hyphenated (e.g. `integrated-information-theory`)
- Always check existing slugs before creating duplicates: `nanograph run --db readings.nano --query readings.gq --name allPapers`
- Append to `seed.jsonl` -- never overwrite it. The file is the source of truth.
