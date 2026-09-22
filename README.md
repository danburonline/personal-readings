# Personal Readings

Personal collection of scientific papers, essays, and technical documents. Device annotations are not uniformly embedded in the archived PDFs.

Use this public repository and its graph only for public literature, source-grounded reading notes and research metadata intended for public sharing. Keep private plans, project mappings, correspondence and account exports outside the repository.

## Reading Sources

The PDFs here are one part of Daniel's reading corpus. Book highlights are also held in Readwise, and the public book catalogue and reading shelves are on [Goodreads](https://goodreads.com/danburonline).

| Source | Contents | Access and use |
| ------ | -------- | -------------- |
| This repository | Scientific papers, essays, technical documents, local annotations, and their knowledge graph | Read the archived source and inspect visible annotations; use the graph for relationships within the collection |
| Readwise and Reader | Book highlights and notes in Readwise; saved documents and their highlights in Reader | Requires authorised account access through the service's interfaces; see [optional CLI examples](#optional-readwise-cli) |
| [Goodreads profile](https://goodreads.com/danburonline) and [read shelf](https://www.goodreads.com/review/list/188819813?shelf=read) | Public book listings and reading status | Identify books Daniel has read, then search Readwise by title or author for the associated highlights |

Goodreads listings are public metadata, not a public copy of the Readwise library or a licence to redistribute book text. A listed book does not establish that its full text is locally available or that every passage has been highlighted. Check the relevant source rather than assuming complete coverage or synchronisation between services.

## Structure

Papers are organised into topic directories:

| Directory                                  | Focus                                                           |
| ------------------------------------------ | --------------------------------------------------------------- |
| `ai_consciousness_and_ethics/`             | Moral status of AI, machine consciousness criteria              |
| `biophysical_mechanisms/`                  | Electromagnetic, thermodynamic, quantum, and microtubular models |
| `bioprinting_and_biofabrication/`          | 3D bioprinting, tissue fabrication techniques                   |
| `brain_plasticity_and_gliomas/`            | Neuroplasticity, glioma biology and modelling                   |
| `brain_preservation_and_ex_vivo_models/`   | Fixation, cryopreservation, ex vivo tissue models               |
| `cellular_and_circuit_neuroscience/`       | Neuronal morphology, cell types, dendrites, and synapses        |
| `cognition_and_representation/`            | Cognitive representation, simulation, emotion, and cognition   |
| `computational_neuroscience/`              | Broad and cross-scale computational accounts of the brain       |
| `consciousness_theories/`                  | Broad and integrative theories of consciousness                 |
| `machine_learning_and_generative_models/`  | Deep learning architectures, generative methods                 |
| `mathematical_and_formal_models/`          | Formal measures, information theory, and mathematical structure |
| `mind_uploading_and_digital_minds/`        | Whole-brain emulation, substrate independence                   |
| `network_science_and_dynamics/`            | Network topology, criticality, synchrony, and dynamical regimes |
| `neural_interfaces_and_neuromodulation/`   | BCI, stimulation paradigms, neural recording                    |
| `neural_regeneration_and_stem_cells/`      | Neurogenesis, stem cell therapies, repair                       |
| `neural_simulation_and_computation/`       | Spiking models, neural mass models, and brain simulation        |
| `neural_tissue_engineering_and_organoids/` | Cerebral organoids, engineered neural tissue                    |
| `neuromorphic_computing/`                  | Neuromorphic hardware, spiking network chips                    |
| `phenomenology_and_experience/`            | Qualia, valence, altered states, and phenomenal structure       |
| `philosophy_of_mind/`                      | Personal identity, functionalism, qualia                        |
| `scientific_methods_and_validation/`       | Consciousness detection, falsification, and validation          |
| `spatial_cognition_and_navigation/`        | Grid cells, path integration, and navigational coding           |
| `theoretical_physics/`                     | Foundations, quantum mechanics, mathematical physics            |
| `virtual_reality_and_simulation/`          | Simulation theory, VR neuroscience applications                 |

## Naming Convention

```txt
YYYYMMDD_descriptive_title.pdf
```

The date prefix represents when the paper was added to the collection, not the publication date. The descriptive portion uses lowercase ASCII `snake_case`: convert spaces and hyphens to single underscores, with no whitespace, uppercase letters, repeated separators, or trailing underscore. The graph paper slug starts as the filename without the `.pdf` extension and is then frozen: renaming the PDF updates `filename`, `path`, `folder`, and `InFolder`, not `slug` or edge endpoints.

## Workflow

1. **Find** a paper or document online and retain an untouched source copy
2. **Rename** the archival file with a `YYYYMMDD_` date prefix (date of discovery, not publication)
3. **Read** -- highlight passages, write margin notes, and work through derivations
4. **Archive** the canonical PDF in the appropriate topic folder and append its Paper node and InFolder edge to `_graph/seed.jsonl`
5. **Extract** each desired mode separately. `python3 _graph/extract.py <pdf> --append` runs metadata only; use `--mode figures|claims|relations|methods|definitions|open-questions` for the other passes
6. **Normalise** with `python3 _graph/build_seed.py --write` so metadata, claims, and methods collapse to one Paper node per slug
7. **Graph** -- reload the compiled database: `nanograph load --db _graph/readings.nano --data _graph/seed.jsonl --mode merge`

## Annotations

Reading annotations may include:

- **Highlights** -- key claims, definitions, results
- **Margin notes** -- questions, cross-references to other papers, disagreements
- **Inline scribbles** -- derivation checks, alternative formulations

Visible marks may be flattened into page content. Preserve an untouched source copy and the canonical archived PDF as separate files when both exist.

## Auxiliary Files

The repository may contain extracted artefacts alongside the PDFs:

- **Notes** (`.md`, `.txt`) -- reading summaries, key takeaways, or synthesis across papers
- **Extracted data** (`.json`, `.csv`) -- structured metadata, citation graphs, or parsed content
- **RAG indices** -- embeddings, chunks, or vector store files used for retrieval-augmented generation over the collection

These are generated as part of working with and querying the collection programmatically.

## Tooling

The collection is indexed and queried through multiple tools:

- **CLI agents** -- used for extracting content, generating summaries, building indices, and ad-hoc queries against the documents
- **Any additional RAG or embedding tooling** as needed -- the repository is tool-agnostic; anything that can ingest PDFs and produce useful retrieval is fair game

### Optional Readwise CLI

Readwise is an optional external source, not a repository dependency. With authorised account access, its CLI can retrieve highlights and document metadata alongside the local collection. Any compatible interface can be used; no particular agent or local environment is assumed.

```bash
# Discover current command options
readwise --help

# Retrieve recent highlights with book identity and notes
readwise readwise-list-highlights --page-size 5 --response-fields text,note,book_id,book_title,book_author --json

# Search book/article highlights by topic
readwise readwise-search-highlights --vector-search-term "consciousness" --limit 5 --json

# Browse Reader documents separately from the Readwise highlight library
readwise reader-list-documents --location new --limit 5 --response-fields title,author --json
```

Match books by title and author, preserve source identifiers and locations, and distinguish quoted text from notes and interpretation. Follow pagination when complete retrieval is required; a limited search is not a complete inventory. External highlights are not automatically mirrored into this repository or its graph. Credentials and private account exports do not belong in the public repository.

## Knowledge Graph

The collection includes a [nanograph](https://github.com/nanograph/nanograph) property graph that models relationships between papers, authors, and concepts. This enables cross-topic discovery, citation traversal, and impact analysis that folder structure and semantic search alone cannot provide.

### Files

| File                    | Purpose                                                            |
| ----------------------- | ------------------------------------------------------------------ |
| `_graph/readings.pg`    | Schema for all node and edge types                                 |
| `_graph/readings.gq`    | Named queries for catalogue, relations, completeness, and coverage |
| `_graph/seed.jsonl`     | Canonical graph data as JSONL                                      |
| `_graph/extract.py`     | Multi-mode Gemini extraction into graph records                    |
| `_graph/build_seed.py`  | Canonicalise duplicate records; refuse conflicting field values    |
| `_graph/rebuild.py`     | Build, validate and optionally activate a database with a backup    |
| `_graph/readings.nano/` | Derived database, gitignored and rebuilt from the schema and JSONL |

Use the graph to find papers and follow relationships, then verify scientific claims against the archived PDF and its page or section. `_graph/seed.jsonl` is authoritative for graph records; it is not a replacement for source evidence. Coverage is partial, and an absent edge does not establish that a relationship does not exist. No background process keeps the graph synchronised.

### Quick Reference

```bash
# Install the current CLI
brew tap nanograph/tap
brew install nanograph/tap/nanograph
nanograph --version  # requires 1.3 or later

# Build and validate separately; leave any active database unchanged
python3 _graph/rebuild.py

# First setup, or activate a fresh full rebuild after stopping database users
python3 _graph/rebuild.py --activate

# Run a query
nanograph run --db _graph/readings.nano --query _graph/readings.gq --name papersPerFolder
nanograph run --db _graph/readings.nano --query _graph/readings.gq --name papersByFolder --param folder=consciousness_theories

# Add data (e.g. new paper)
# Append to seed.jsonl, inspect canonicalisation, then reload if conflict-free:
python3 _graph/build_seed.py
python3 _graph/build_seed.py --write
nanograph load --db _graph/readings.nano --data _graph/seed.jsonl --mode merge

# Inspect
nanograph describe --db _graph/readings.nano
nanograph lint --db _graph/readings.nano --query _graph/readings.gq
nanograph doctor --db _graph/readings.nano --schema _graph/readings.pg --verbose
```

### Graph maintenance

Run examples from the repository root. The rebuild helper needs Python 3 and Nanograph on `PATH`; extraction also needs authorised Gemini access. This repository intentionally has no `nanograph.toml`, so direct Nanograph commands must pass their database, schema and query paths explicitly.

Use one seed writer at a time. Stop manual seed editors and other writers before appending, canonicalising or rebuilding, not just before activation. `extract.py --append`, `build_seed.py --write` and `rebuild.py` share an advisory `seed.jsonl.write-lock` and fail fast on contention. Extraction holds it for the whole append run, including API waits. Direct Nanograph commands and arbitrary editors do not honour this lock; it is not a filesystem permission or universal transaction mechanism.

Canonicalisation checks that the seed is unchanged immediately before replacing it; extraction checks before each append. These checks detect intervening edits but cannot eliminate a simultaneous write from an uncooperative editor. If a check fails, inspect the current seed and rerun from that state; do not force an older result over it.

`rebuild.py` copies the schema, seed and saved queries into a uniquely named ignored staging directory, then runs `init`, `load --mode overwrite`, `lint` and `doctor` against that snapshot. It checks that the sources remain unchanged before reporting validation or activating. By default it leaves the active database untouched. `--activate` builds and validates a fresh stage, then moves any existing database to an unused `readings.nano.backup-<id>` directory before activating the new one. A failed activation restores the old database when the destination is unoccupied. Stop other database clients before activation. Never combine backup database contents with the canonical seed.

Failed stages, backups and generated configuration stay in ignored build artefacts for inspection; the helper does not delete them or rewrite PDFs or the seed. A `readings.nano.rebuild-lock` also protects helper builds. If a process is interrupted, first establish that its owning process has stopped, then remove only its abandoned empty lock directory or directories before retrying. Never remove an active lock to get past contention. After changing saved queries, run `nanograph lint`; after changing schema or removing graph records, use a complete staged rebuild rather than `load --mode merge`.

#### Corrections and repeated extraction

Normal extraction appends enrichment. Canonicalisation fills missing fields but does not choose between conflicting non-empty assertions: `build_seed.py --write` refuses such conflicts and leaves the seed unchanged. Inspect its dry-run report before writing.

For an authorised correction, check the source PDF, edit the affected canonical field or edge explicitly, and record the source location and reason in the associated reading note or change description. Resolve any conflicting proposed duplicate against that evidence, keeping one node per key. Preserve frozen Paper slugs and historical Extraction records. Canonicalise and inspect the diff. Stop database clients and seed writers, then run `python3 _graph/rebuild.py --activate` to build, validate and activate a fresh database without retained obsolete edges. Query the corrected claims or relationships and `extractionsByPaper` in the active database before reporting the correction complete. Running the helper without `--activate` validates only a separate stage.

Each new extraction attempt has a unique `{paper_slug}--{mode}--{run_id}` identity. Failed attempts and successful retries coexist; legacy `{paper_slug}--{mode}` records remain valid and are not rewritten. Re-extraction does not overwrite curated assertions or convert historical unknown provenance into a verified record. `result_status=ok` means the response passed the mode's structural checks and output processing, which can accept explicit empty collections; it does not mean the claims have been reviewed. Missing collections, malformed field types and handled model or output-processing exceptions produce a failed run, discard proposed outputs and cache changes, and let the batch continue. Abrupt termination or filesystem failure can prevent provenance from being written. Use `extractionsByPaper` to inspect attempt, model, PDF checksum and review status separately from output edges. Run a named paper without `--append` to review proposed re-extraction output before ingestion; API use still requires authorisation.

Run the offline maintenance tests with `python3 -B -m unittest discover -s _graph/tests -v`. The optional Nanograph integration test uses a synthetic graph in a temporary directory, never the active database.

### Available Queries

| Query                      | Parameters   | Description                                      |
| -------------------------- | ------------ | ------------------------------------------------ |
| `allPapers`                | --           | Full catalogue, sorted by date added             |
| `allFolders`               | --           | List all topic folders                           |
| `papersPerFolder`          | --           | Paper counts per topic folder                    |
| `paperDetails`             | `paper`      | All stored fields for one paper, including path  |
| `papersByFolder`           | `folder`     | Papers in a given topic directory                |
| `papersByConcept`          | `concept`    | Papers covering a given concept                  |
| `papersByAuthor`           | `author`     | Papers by a given author                         |
| `papersByTechnique`        | `technique`  | Papers using a technique                         |
| `citedBy`                  | `paper`      | Papers that cite a given paper                   |
| `citesWhat`                | `paper`      | Papers cited by a given paper                    |
| `extendsWhat`              | `paper`      | Papers a paper extends                           |
| `extendedBy`               | `paper`      | Papers that extend a given paper                 |
| `contradictsWhat`          | `paper`      | Papers a paper contradicts                       |
| `contradictedBy`           | `paper`      | Papers that contradict a given paper             |
| `extendsPerPaper`          | --           | Extends counts, highest degree first             |
| `contradictsPerPaper`      | --           | Contradicts counts, highest degree first         |
| `techniquesByPaper`        | `paper`      | Techniques used by a paper                       |
| `definitionsByTerm`        | `term`       | Definitions of a term across papers              |
| `definitionsByPaper`       | `paper`      | Definitions extracted from a paper               |
| `figuresByPaper`           | `paper`      | Figures extracted from a paper                   |
| `claimsByPaper`            | `paper`      | Claims extracted from a paper                    |
| `openQuestionsByPaper`     | `paper`      | Open questions extracted from a paper            |
| `extractionsByPaper`       | `paper`      | Extraction provenance records for a paper        |
| `papersMissingMetadata`    | --           | Papers with no WrittenBy edge                    |
| `papersMissingFigures`     | --           | Papers with no HasFigure edge                    |
| `papersMissingClaims`      | --           | Papers with no MakesClaim edge                   |
| `papersMissingRelations`   | --           | Papers with no Extends and no Contradicts        |
| `papersMissingMethods`     | --           | Papers with no UsesTechnique edge                |
| `papersMissingDefinitions` | --           | Papers with no HasDefinition edge                |
| `papersMissingQuestions`   | --           | Papers with no Raises edge                       |

The `papersMissing*` queries identify missing output relationships, not whether an extraction mode was attempted. A successful extraction that found no figures or relations can still appear here. Check `extractionsByPaper` for processing and review status; unknown historical fields must remain unknown.

### Enrichment

The seed data contains paper nodes extracted from filenames. To enrich the graph over time:

1. **Authors** -- add Author nodes and WrittenBy edges
2. **Concepts** -- add Concept nodes and Covers edges to map conceptual coverage
3. **Citations** -- add Cites/Extends/Contradicts edges between papers in the collection
4. **Provenance** -- Extraction nodes record which mode, model, and PDF bytes produced a run

Append new records to `_graph/seed.jsonl`, keep one node per `(type, slug)` key, then run `nanograph load --db _graph/readings.nano --data _graph/seed.jsonl --mode merge`.

## Agent Instructions

Start with [AGENTS.md](AGENTS.md) and the repository-local [nanograph skill](.agents/skills/nanograph/SKILL.md). For literature discovery and relationship questions, query the graph, inspect extraction provenance, then read the canonical PDFs. Fall back to file search where coverage is incomplete. The skill is scoped to this library, not other repositories, and automatic discovery depends on the agent application. A portable explicit instruction is: “Read AGENTS.md and the nanograph skill, use the graph to find relevant papers, then verify their source text.”

Key constraints:

- Write in **British English**
- Maintain scientific precision -- exact terminology, explicit uncertainty and limitations, no unsupported simplification
- No AI-typical wording ("delve", "crucial", "it's important to note", etc.)
- No em dashes -- use double hyphens or restructure the sentence
- All output should read as if written by a researcher, not generated by a model

Agents working in this repository are expected to extract, summarise, and reason over scientific material with the same rigour as the source texts.

## Usage

This is a working research library, not an archive. Papers get added, re-read, and cross-referenced as part of ongoing work in computational neuroanatomy, consciousness science, and mathematical modelling.
