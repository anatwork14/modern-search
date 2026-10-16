# Desktop UX specification

## Design goal

A research workbench closer to a scholarly discovery tool than a chat thread: powerful but comprehensible search, meaningful groups, grounded evidence, minimal steps between discovery and saving a reading list. macOS-native feel without over-decorative effects that compromise information density.

## Primary layout

~~~text
┌────────────────────────────────────────────────────────────────────────────┐
│ Modern Search  [global research query____________________]  [Search]       │
│ Scope [Local library v]  Mode [Strict | Broad | Bridge]  [Sync/Offline]    │
├───────────────────┬──────────────────────────────────────┬─────────────────┤
│ FACETS            │ RESULTS / GROUPS                     │ PAPER INSPECTOR │
│ Field / Task      │ [Group by bottleneck/method/domain]   │ Title + authors │
│ Method / Model    │ [2,478 discovered ≠ indexed count]   │ Evidence state  │
│ Objective / Data  │ Paper title + year + venue evidence   │ Abstract        │
│ Venue / Year      │ Match routes + excerpt if available  │ Contributions   │
│ Verification QA   │ Tag role + PDF availability          │ Citation/PDF    │
│ AND/OR/NOT        │ Cursor pagination                    │ Tag review      │
└───────────────────┴──────────────────────────────────────┴─────────────────┘
~~~

Layout adapts to laptop sizes with collapsible filters and inspector. Keyboard-first navigation, visible focus, stable screen reader labels, readable typography and color-independent evidence states.

## Screens and interactions

1. **Onboarding/import**: choose local folder / connect Drive / import workbook snapshot; clarify network and privacy; progress and audit summary; model optional download status and storage estimates measured on device.
2. **Search**: one prominent NL query field accepting Vietnamese and English; query interpretation toggle; strict/broad/bridge scope and offline/online badge; advanced filter builder with nested ANY/ALL/NOT, saved filter sets, live counts.
3. **Results**: ranked or grouped list; every result shows title, authors, year, venue+rank evidence and its vintage, tags/role, source link, what matched, candidate-vs-verified status and fulltext availability. Explain why chosen and why excluded when relevant.
4. **Paper inspector**: abstract, author-stated contributions, limitations, figures if available, source passage(s) with actual page references, citation graph when supported, code/dataset links, review status and edit tags.
5. **Concept explorer**: multi-method facets, re-group by mechanism/bottleneck, group paper counts and overlap matrix; graph is optional, text/list navigation primary.
6. **Compare papers**: matrix of research question, method, datasets, metrics, reported outcome, constraints, limitation and evidence. Unknowns remain blank or 'not extracted', never guessed.
7. **Reading workspace**: pinned seeds, collections, priority, notes, annotation review queue, saved queries with query AST, export BibTeX/CSV/Markdown (respect copyright and source restrictions).
8. **Data/settings**: import/sync logs, verified PDF counts, indexed-abstract/section counts, model ID/dimension/index version, reindex, backup/restore, external connections and opt-in switches.
9. **Evaluation view (developer)**: query-level regression table, relevance labels, rank comparison, p50/p95 and query failures. Hide unless expert mode.

## Key components and behavior

- Facet chips are always labeled with canonical namespace; aliases appear as friendly search suggestions but save canonical tag ID.
- Facet counts reflect current constrained corpus, not global spreadsheet counts.
- Selecting tags in same facet defaults ANY with explicit ALL toggle; facets combine AND; NOT is visible.
- Query plan viewer shows hard filters separately from semantically expanded soft concepts.
- A ranked card has a reason code: exact phrase, indexed abstract, verified tag, candidate tag, semantic similarity, citation neighbor or hypothesized analogy.
- Search results display an explicit scope such as "Indexed: N abstracts / M PDFs; Candidate papers: K", calculated from local DB, never hardcoded.
- "Open PDF at page" only appears when a validated local PDF and page mapping exist; otherwise show source URL.
- Zero-state shows hard filters preventing match, offers "Broaden query" as a user action, and preserves original query.
- Save query preserves original text and parsed AST; UI reloads identical strict constraints.
- Network icon shows provider and potential data sent; any online query is explicitly initiated.
- Theme: native system/light/dark preference; generous search focus, restrained neutrals, accessible contrast; no essential information conveyed by color alone.

## Suggested interaction flow

User enters "How does attention improve inference?" → app previews search plan → results grouped into IO kernels/KV sharing/KV selection/sparse attention/serving → user chooses "KV selection" → opens evidence excerpt → saves 8 papers to research collection → exports review table. For "FL attention" the app must produce distinct *client aggregation* and *attention inside local model* groups, with combined cases clearly identified.

## UX acceptance criteria

- Every source/state label interpretable without a help article.
- Keyboard search, facet selection, result browsing and inspector usable without mouse.
- Filter changes correctly update result set and counts; impossible strict conjunction yields zero.
- User can identify why each result matched and whether that match is verified.
- UI remains responsive while parsing/embedding asynchronously; cancellation and failures visible.
- Screen snapshots and accessibility smoke tests required when implemented.
