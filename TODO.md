# TODO

## Active

- [ ] Update README.md workflow section -- replace "still evolving" with concrete 6-step workflow now that nanograph is set up
- [ ] Update AGENTS.md -- add Knowledge Graph section so agents know the graph exists, when to update it, and the JSONL format
      [ ] First enrichment pass -- pick 5-10 heavily-read papers and add Author nodes, Concept nodes, Covers edges, and Cites edges to \_graph/seed.jsonl

---

## Habits

Regular maintenance to keep the research library and knowledge graph healthy.

### Per Paper (when adding)

- [ ] Rename: `YYYYMMDD_descriptive_title_pdf.pdf`
- [ ] Archive into correct topic folder
      [ ] Append Paper node + InFolder edge to `_graph/seed.jsonl`
      [ ] Reload: `nanograph load _graph/readings.nano --data _graph/seed.jsonl --mode merge`
- [ ] Git commit

### After Reading (when the paper matters)

- [ ] Extract: ask agent to read annotated PDF and produce key claims, authors, concepts, in-collection citations
      [ ] Enrich `_graph/seed.jsonl`: Author nodes + WrittenBy edges
      [ ] Enrich `_graph/seed.jsonl`: Concept nodes + Covers edges
      [ ] Enrich `_graph/seed.jsonl`: Cites / Extends / Contradicts edges to other papers in collection
      [ ] Enrich `_graph/seed.jsonl`: Informs edges to relevant manuscripts (05-ocm, frontiers-consciousness-engineering, cortical-reorganisation, hybrid-mind-uploading)
      [ ] Reload: `nanograph load _graph/readings.nano --data _graph/seed.jsonl --mode merge`
- [ ] Index to Anara

### Monthly

[ ] Audit: `nanograph describe --db _graph/readings.nano` -- check paper count matches `find . -name "*.pdf" | wc -l`
[ ] Health: `nanograph doctor _graph/readings.nano`

- [ ] Orphans: find papers with zero Covers edges (not yet connected to any concept)
- [ ] Manuscript gaps: check which manuscripts have zero Informs edges
- [ ] Update AGENTS.md if workflows changed
