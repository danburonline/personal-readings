# TODO

Open graph work only. Ingesting a new PDF is in `AGENTS.md`, not here.

- [ ] Replace filename-derived Paper identity with a stable internal key plus separate path, filename, DOI, and arXiv fields
- [ ] Add per-paper, per-mode extraction provenance: model, timestamp, PDF checksum, extraction version, result status, and review status
- [ ] Replace manual append-and-squash Paper updates with a deterministic canonical seed build
- [ ] Review high-degree Extends and Contradicts edges; relation extraction currently infers relationships from titles and discards its justifications
- [ ] Curate Techniques that are actually theories or concepts and normalise the known Author and Concept spelling variants
- [ ] Add queries for extraction completeness, Extends, Contradicts, paper details, and manuscript coverage
- [ ] Populate Informs beyond the current two edges across four Manuscript nodes
