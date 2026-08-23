# Personal Readings

Personal collection of scientific papers, essays, and technical documents. Device annotations are not uniformly embedded in the archived PDFs.

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

The date prefix represents when the paper was added to the collection, not the publication date. Underscores replace spaces. The graph paper slug is the filename without the `.pdf` extension.

## Workflow

1. **Find** a paper or document online and retain an untouched source copy
2. **Rename** the archival file with a `YYYYMMDD_` date prefix (date of discovery, not publication)
3. **Read** on the current device -- highlight passages, write margin notes, and work through derivations
4. **Export** a portable annotated PDF and, where available, a device-native archive; verify visible marks before retiring the device copy
5. **Archive** the canonical PDF in the appropriate topic folder and append its Paper node and InFolder edge to `_graph/seed.jsonl`
6. **Extract** each desired mode separately. `python3 _graph/extract.py <pdf> --append` runs metadata only; use `--mode figures|claims|relations|methods|definitions|open-questions` for the other passes
7. **Normalise** duplicate Paper records emitted by metadata, claims, and methods into one Paper node carrying the union of their fields
8. **Graph** -- reload the compiled database: `nanograph load --db _graph/readings.nano --data _graph/seed.jsonl --mode merge`

## Annotations

Reading annotations may include:

- **Highlights** -- key claims, definitions, results
- **Margin notes** -- questions, cross-references to other papers, disagreements
- **Inline scribbles** -- derivation checks, alternative formulations

An audit on 17 August 2026 found no standard PDF ink, highlight, text-note, or free-text annotation objects and no native reMarkable sidecars in this repository. Existing marks could be flattened into page content, which a structural scan cannot distinguish reliably. Preserve the untouched source, any device-native archive, and a visually verified annotated export as separate files before a device migration.

## Auxiliary Files

The repository may contain extracted artefacts alongside the PDFs:

- **Notes** (`.md`, `.txt`) -- reading summaries, key takeaways, or synthesis across papers
- **Extracted data** (`.json`, `.csv`) -- structured metadata, citation graphs, or parsed content
- **RAG indices** -- embeddings, chunks, or vector store files used for retrieval-augmented generation over the collection

These are generated as part of working with and querying the collection programmatically.

## Tooling

The collection is indexed and queried through multiple tools:

- **OpenCode / CLI agents** -- used for extracting content, generating summaries, building indices, and ad-hoc queries against the documents
- **Any additional RAG or embedding tooling** as needed -- the repository is tool-agnostic; anything that can ingest PDFs and produce useful retrieval is fair game

## Knowledge Graph

The collection includes a [nanograph](https://github.com/nanograph/nanograph) property graph that models relationships between papers, authors, concepts, and manuscripts. This enables cross-topic discovery, citation traversal, and impact analysis that folder structure and semantic search alone cannot provide.

### Files

| File                    | Purpose                                                            |
| ----------------------- | ------------------------------------------------------------------ |
| `_graph/readings.pg`    | Schema for all node and edge types                                 |
| `_graph/readings.gq`    | Seventeen named queries for common operations                      |
| `_graph/seed.jsonl`     | Canonical graph data as JSONL                                      |
| `_graph/extract.py`     | Multi-mode Gemini extraction into graph records                    |
| `_graph/readings.nano/` | Derived database, gitignored and rebuilt from the schema and JSONL |

### Quick Reference

```bash
# Install the current CLI
brew tap nanograph/tap
brew install nanograph/tap/nanograph

# Future complete rebuild through a staging database
nanograph init --db _graph/readings.nano.new --schema _graph/readings.pg
nanograph load --db _graph/readings.nano.new --data _graph/seed.jsonl --mode overwrite
nanograph lint --db _graph/readings.nano.new --query _graph/readings.gq
nanograph doctor --db _graph/readings.nano.new --schema _graph/readings.pg --verbose

# Run a query
nanograph run --db _graph/readings.nano --query _graph/readings.gq --name papersPerFolder
nanograph run --db _graph/readings.nano --query _graph/readings.gq --name papersByFolder --param folder=consciousness_theories

# Add data (e.g. new paper)
# Append to seed.jsonl, then:
nanograph load --db _graph/readings.nano --data _graph/seed.jsonl --mode merge

# Inspect
nanograph describe --db _graph/readings.nano
nanograph lint --db _graph/readings.nano --query _graph/readings.gq
nanograph doctor --db _graph/readings.nano --schema _graph/readings.pg --verbose
```

Nanograph 1.3.0 was installed and the active database was rebuilt from the canonical seed on 17 August 2026. It now uses the `namespace-lineage` storage generation, manifest format 3, and `db_version: 1`; `lint` passes all 17 queries and `doctor` passes all 25 datasets. The stale pre-v1.2 database is preserved at `_graph/readings.nano.legacy-v3/` for rollback only. Do not merge it into the active graph.

This repository intentionally has no `nanograph.toml`. Run Nanograph from the repository root and pass `--db`, `--schema`, and `--query` paths explicitly. If `nanograph init` generates a configuration scaffold under `_graph/`, remove it after the staged rebuild.

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
| `papersByTechnique`   | `technique`  | Papers using a technique              |
| `citedBy`             | `paper`      | Papers that cite a given paper        |
| `citesWhat`           | `paper`      | Papers cited by a given paper         |
| `papersForManuscript` | `manuscript` | Papers informing a given manuscript   |
| `techniquesByPaper`   | `paper`      | Techniques used by a paper            |
| `definitionsByTerm`   | `term`       | Definitions of a term across papers   |
| `definitionsByPaper`  | `paper`      | Definitions extracted from a paper    |
| `figuresByPaper`      | `paper`      | Figures extracted from a paper        |
| `claimsByPaper`       | `paper`      | Claims extracted from a paper         |
| `openQuestionsByPaper` | `paper`      | Open questions extracted from a paper |

### Enrichment

The seed data contains paper nodes extracted from filenames. To enrich the graph over time:

1. **Authors** -- add Author nodes and WrittenBy edges
2. **Concepts** -- add Concept nodes and Covers edges to map conceptual coverage
3. **Citations** -- add Cites/Extends/Contradicts edges between papers in the collection
4. **Manuscripts** -- add Informs edges from papers to Daniel's manuscripts

Append new records to `_graph/seed.jsonl`, keep one node per `(type, slug)` key, then run `nanograph load --db _graph/readings.nano --data _graph/seed.jsonl --mode merge`.

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
