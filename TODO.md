# TODO

## Active

- [x] Install nanograph 1.3.0 through Homebrew and verify it in fresh zsh sessions (17 August 2026)
- [x] Rebuild, lint, doctor, and activate `_graph/readings.nano/` from the canonical seed; preserve the legacy v3 store at `_graph/readings.nano.legacy-v3/` (17 August 2026)
- [ ] Pilot three representative PDFs on the Kindle Scribe and verify an export round trip before bulk upload
- [ ] Re-export any reMarkable-native annotations that still exist on the old device; this repository contains no native annotation sidecars or standard note/highlight/ink objects

## Deferred PDF changes

The 17 August 2026 decision is to leave the PDFs in their current state. Duplicate consolidation, further filename cleanup, OCR derivatives, PDF repairs, and second-level folder changes are not active tasks.

## Graph improvements

- [ ] Replace filename-derived Paper identity with a stable internal key plus separate path, filename, DOI, and arXiv fields
- [ ] Add per-paper, per-mode extraction provenance: model, timestamp, PDF checksum, extraction version, result status, and review status
- [ ] Replace manual append-and-squash Paper updates with a deterministic canonical seed build
- [ ] Review high-degree Extends and Contradicts edges; relation extraction currently infers relationships from titles and discards its justifications
- [ ] Curate Techniques that are actually theories or concepts and normalise the known Author and Concept spelling variants
- [ ] Add queries for extraction completeness, Extends, Contradicts, paper details, and manuscript coverage
- [ ] Populate Informs beyond the current two edges across four Manuscript nodes
- [ ] Add recursive path support and a subfolder model before introducing second-level topic folders

## Per paper

- [ ] Preserve an untouched source PDF
- [ ] Name the archival file `YYYYMMDD_descriptive_title.pdf`
- [ ] Archive it in the correct topic folder
- [ ] Append one Paper node and one InFolder edge to `_graph/seed.jsonl`
- [ ] Run each desired extraction mode separately
- [ ] Keep one canonical Paper node per slug before loading
- [ ] Reload with `nanograph load --db _graph/readings.nano --data _graph/seed.jsonl --mode merge`
- [ ] Commit the PDF, seed update, and any reading notes together

## After reading

- [ ] Preserve the device-native archive where available
- [ ] Export and visually verify a portable annotated PDF
- [ ] Capture visible annotations, key claims, authors, concepts, techniques, and in-collection citations
- [ ] Add relevant Informs edges to active manuscripts

## Monthly

- [ ] Compare the Paper count with `find . -name "*.pdf" | wc -l`
- [ ] Run `nanograph lint --db _graph/readings.nano --query _graph/readings.gq`
- [ ] Run `nanograph doctor --db _graph/readings.nano --schema _graph/readings.pg --verbose`
- [ ] Check for duplicate keys, orphan endpoints, folder mismatches, unreviewed extraction runs, and papers with no Covers edges
- [ ] Update `README.md`, `AGENTS.md`, and the nanograph skill when the workflow changes
