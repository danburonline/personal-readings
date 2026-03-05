# Personal Readings

Personal collection of annotated scientific papers, essays, and technical documents. Most PDFs carry highlights, margin notes, and inline scribbles from active reading sessions.

## Structure

Papers are organised into topic directories:

| Directory                                  | Focus                                                |
| ------------------------------------------ | ---------------------------------------------------- |
| `ai_consciousness_and_ethics/`             | Moral status of AI, machine consciousness criteria   |
| `bioprinting_and_biofabrication/`          | 3D bioprinting, tissue fabrication techniques        |
| `brain_plasticity_and_gliomas/`            | Neuroplasticity, glioma biology and modelling        |
| `brain_preservation_and_ex_vivo_models/`   | Fixation, cryopreservation, ex vivo tissue models    |
| `computational_neuroscience/`              | Connectomics, network topology, neural computation   |
| `consciousness_theories/`                  | IIT, GWT, higher-order theories, formal models       |
| `machine_learning_and_generative_models/`  | Deep learning architectures, generative methods      |
| `mind_uploading_and_digital_minds/`        | Whole-brain emulation, substrate independence        |
| `neural_interfaces_and_neuromodulation/`   | BCI, stimulation paradigms, neural recording         |
| `neural_regeneration_and_stem_cells/`      | Neurogenesis, stem cell therapies, repair            |
| `neural_tissue_engineering_and_organoids/` | Cerebral organoids, engineered neural tissue         |
| `neuromorphic_computing/`                  | Neuromorphic hardware, spiking network chips         |
| `philosophy_of_mind/`                      | Personal identity, functionalism, qualia             |
| `theoretical_physics/`                     | Foundations, quantum mechanics, mathematical physics |
| `virtual_reality_and_simulation/`          | Simulation theory, VR neuroscience applications      |

## Naming Convention

```txt
YYYYMMDD_descriptive_title_pdf.pdf
```

The date prefix represents when the paper was added to the collection, not the publication date. Underscores replace spaces; `_pdf` is appended before the extension.

## Workflow

1. **Find** a paper or document online
2. **Rename** the file with a `YYYYMMDD_` date prefix (date of discovery, not publication)
3. **Read** on a reMarkable tablet -- highlight passages, scribble margin notes, work through derivations
4. **Archive** the annotated PDF into the appropriate topic folder in this repository
5. **Extract** (optional) -- generate reading notes, markdown summaries, or structured metadata as needed
6. **Index** -- add the document to Anara and any other RAG providers for retrieval

Steps 5 and 6 are still evolving. The extraction and indexing pipeline is not yet fully settled.

## Annotations

All reading and annotation happens on a reMarkable tablet. Expect:

- **Highlights** -- key claims, definitions, results
- **Margin notes** -- questions, cross-references to other papers, disagreements
- **Inline scribbles** -- derivation checks, alternative formulations

These annotations are embedded in the PDF files themselves.

## Auxiliary Files

The repository may contain extracted artefacts alongside the PDFs:

- **Notes** (`.md`, `.txt`) -- reading summaries, key takeaways, or synthesis across papers
- **Extracted data** (`.json`, `.csv`) -- structured metadata, citation graphs, or parsed content
- **RAG indices** -- embeddings, chunks, or vector store files used for retrieval-augmented generation over the collection

These are generated as part of working with and querying the collection programmatically.

## Tooling

The collection is indexed and queried through multiple tools:

- **[Anara](https://anara.ai)** -- primary RAG provider for semantic search and retrieval over the PDF corpus
- **OpenCode / CLI agents** -- used for extracting content, generating summaries, building indices, and ad-hoc queries against the documents
- **Any additional RAG or embedding tooling** as needed -- the repository is tool-agnostic; anything that can ingest PDFs and produce useful retrieval is fair game

## Knowledge Graph

The collection includes a [nanograph](https://github.com/aaltshuler/nanograph) property graph that models relationships between papers, authors, concepts, and manuscripts. This enables cross-topic discovery, citation traversal, and impact analysis that folder structure and semantic search alone cannot provide.

### Files

| File             | Purpose                                                                                                                                                   |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `readings.pg`    | Schema -- node types (Paper, Author, Concept, TopicFolder, Manuscript) and edge types (Cites, Extends, Contradicts, WrittenBy, Covers, InFolder, Informs) |
| `readings.gq`    | Canned queries -- 10 named queries for common operations                                                                                                  |
| `seed.jsonl`     | Data -- all papers, topic folders, and manuscripts as JSONL                                                                                               |
| `readings.nano/` | Compiled database (gitignored, rebuilt from schema + data)                                                                                                |

### Quick Reference

```bash
# Rebuild the database from scratch
nanograph init readings.nano --schema readings.pg
nanograph load readings.nano --data seed.jsonl --mode overwrite

# Run a query
nanograph run --db readings.nano --query readings.gq --name papersPerFolder
nanograph run --db readings.nano --query readings.gq --name papersByFolder --param folder=consciousness_theories

# Add data (e.g. new paper)
# Append to seed.jsonl, then:
nanograph load readings.nano --data seed.jsonl --mode merge

# Inspect
nanograph describe --db readings.nano
nanograph check --db readings.nano --query readings.gq
```

### Available Queries

| Query                 | Parameters   | Description                           |
| --------------------- | ------------ | ------------------------------------- |
| `allPapers`           | --           | Full catalogue, sorted by date added  |
| `allFolders`          | --           | List all topic folders                |
| `papersPerFolder`     | --           | Paper counts per topic folder         |
| `allManuscripts`      | --           | Daniel's manuscripts and their status |
| `papersByFolder`      | `folder`     | Papers in a given topic directory     |
| `papersByConcept`     | `concept`    | Papers covering a given concept       |
| `papersByAuthor`      | `author`     | Papers by a given author              |
| `citedBy`             | `paper`      | Papers that cite a given paper        |
| `citesWhat`           | `paper`      | Papers cited by a given paper         |
| `papersForManuscript` | `manuscript` | Papers informing a given manuscript   |

### Enrichment

The seed data contains paper nodes extracted from filenames. To enrich the graph over time:

1. **Authors** -- add Author nodes and WrittenBy edges
2. **Concepts** -- add Concept nodes and Covers edges to map conceptual coverage
3. **Citations** -- add Cites/Extends/Contradicts edges between papers in the collection
4. **Manuscripts** -- add Informs edges from papers to Daniel's manuscripts

Use `nanograph load readings.nano --data new_data.jsonl --mode merge` to incrementally add data without overwriting.

## Agent Instructions

An `AGENTS.md` file at the repository root governs how AI agents operate within this workspace. Key constraints:

- Write in **British English**
- Maintain scientific precision -- exact terminology, no hedging, no simplification
- No AI-typical wording ("delve", "crucial", "it's important to note", etc.)
- No em dashes -- use double hyphens or restructure the sentence
- All output should read as if written by a researcher, not generated by a model

Agents working in this repository are expected to extract, summarise, and reason over scientific material with the same rigour as the source texts.

## Usage

This is a working research library, not an archive. Papers get added, re-read, and cross-referenced as part of ongoing work in computational neuroanatomy, consciousness science, and mathematical modelling.
