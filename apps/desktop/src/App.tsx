import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { LogicalSize } from "@tauri-apps/api/dpi";
import { getCurrentWindow } from "@tauri-apps/api/window";
import type { SearchData, SearchMode, SearchRequest, SearchResult } from "./contracts";
import { mockSearch } from "./mock";
import { getHealth, isDesktopRuntime, searchLocal } from "./service";
import "./App.css";

const emptySearch: SearchData = {
  results: [],
  total: 0,
  next_cursor: null,
  index_version: "unknown",
  dense_status: "unavailable",
  warnings: [],
};

function displayError(error: unknown): string {
  if (typeof error === "string") return error;
  if (error instanceof Error) return error.message;
  if (error && typeof error === "object" && "message" in error && typeof error.message === "string") {
    return error.message;
  }
  return "The local search request failed. Check that the service is available.";
}

function routeLabel(route: string): string {
  return route.replaceAll("_", " ").toLowerCase();
}

function formatCitation(paper: SearchResult): string {
  const authors = paper.authors.length ? paper.authors.join(", ") : "Unknown authors";
  const year = paper.year ? ` (${paper.year})` : "";
  const venue = paper.venue ? `. ${paper.venue}` : "";
  const doi = paper.doi ? `. https://doi.org/${paper.doi}` : "";
  return `${authors}${year}. ${paper.title}${venue}${doi}.`;
}

async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

function SafeEvidenceLink({ href, children }: { href?: string | null; children: string }) {
  if (!href || !/^https?:\/\//i.test(href)) return null;
  return <a href={href} target="_blank" rel="noreferrer">{children}</a>;
}

function PaperCard({
  paper,
  isSelected,
  onSelect,
  cardRef,
}: {
  paper: SearchResult;
  isSelected?: boolean;
  onSelect?: () => void;
  cardRef?: (el: HTMLElement | null) => void;
}) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const verifiedTags = paper.tags.filter((tag) => tag.review_state === "verified");
  const candidateTags = paper.tags.filter((tag) => tag.review_state === "needs-manual-review");

  const handleCopy = async (key: string, text: string) => {
    const ok = await copyToClipboard(text);
    if (ok) {
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 1500);
    }
  };

  return (
    <article
      ref={cardRef}
      className={`paper-card ${isSelected ? "is-selected" : ""}`}
      tabIndex={0}
      onClick={onSelect}
      aria-selected={isSelected}
    >
      <div className="paper-heading">
        <div>
          <p className="eyebrow">{paper.paper_id}</p>
          <h3>{paper.title}</h3>
        </div>
        <span className={`state-pill ${paper.review_state === "manually-verified" ? "verified" : "candidate"}`}>
          {paper.review_state.replaceAll("-", " ")}
        </span>
      </div>
      <p className="paper-meta">
        {paper.authors.length ? paper.authors.join(", ") : "Author details unavailable"}
        {paper.year ? ` · ${paper.year}` : " · Year unavailable"}
        {paper.venue ? ` · ${paper.venue}` : ""}
      </p>
      <p className="paper-abstract">{paper.abstract ?? "No abstract is available in the local index."}</p>
      <details className="paper-inspector">
        <summary>Evidence & tags</summary>
        {paper.venue_evidence?.length ? (
          <div className="venue-evidence" aria-label="Source-reported venue evidence">
            <strong>Source-reported venue evidence</strong>
            <span className="muted">Displayed as supplied; not independently verified here.</span>
            {paper.venue_evidence.map((evidence, index) => (
              <div className="venue-evidence-item" key={`${evidence.ranking_system ?? "source"}-${evidence.ranking_year ?? "unknown"}-${index}`}>
                <span>{[evidence.venue_type, evidence.ranking_system, evidence.core_rank, evidence.sjr_quartile, evidence.ranking_category]
                  .filter(Boolean).join(" · ") || "Ranking details unavailable"}</span>
                <span>Ranking year: {evidence.ranking_year ?? "not supplied"}</span>
                <div className="venue-links">
                  <SafeEvidenceLink href={evidence.ranking_source_url}>Ranking source</SafeEvidenceLink>
                  <SafeEvidenceLink href={evidence.publication_evidence_url}>Publication evidence</SafeEvidenceLink>
                </div>
              </div>
            ))}
          </div>
        ) : null}
        <div className="evidence-row">
          <span className="evidence-label">Matched by</span>
          {paper.match_routes.length ? paper.match_routes.map((route) => (
            <span className="route-chip" key={route}>{routeLabel(route)}</span>
          )) : <span className="muted">No match reason supplied</span>}
        </div>
        <div className="evidence-row">
          <span className="evidence-label">Tags</span>
          {verifiedTags.map((tag) => <span className="tag verified-tag" key={tag.tag_id}>{tag.tag_id} · verified</span>)}
          {candidateTags.map((tag) => <span className="tag candidate-tag" key={tag.tag_id}>{tag.tag_id} · candidate</span>)}
          {!verifiedTags.length && !candidateTags.length && <span className="muted">No reviewed tags</span>}
        </div>
      </details>
      <div className="paper-footer">
        <div className="paper-actions-bar">
          {paper.source_url && /^https?:\/\//i.test(paper.source_url) && (
            <a className="action-link" href={paper.source_url} target="_blank" rel="noreferrer">Open source</a>
          )}
          {paper.doi && (
            <button className="copy-action-btn" type="button" onClick={() => void handleCopy("doi", paper.doi!)}>
              {copiedKey === "doi" ? "✓ DOI copied" : "Copy DOI"}
            </button>
          )}
          <button className="copy-action-btn" type="button" onClick={() => void handleCopy("title", paper.title)}>
            {copiedKey === "title" ? "✓ Title copied" : "Copy title"}
          </button>
          <button className="copy-action-btn" type="button" onClick={() => void handleCopy("cite", formatCitation(paper))}>
            {copiedKey === "cite" ? "✓ Citation copied" : "Copy citation"}
          </button>
        </div>
        <span className="pdf-state-text">
          {paper.pdf_state === "VERIFIED_LOCAL" ? "Verified local PDF" : paper.pdf_state === "REMOTE_ONLY" ? "Remote PDF link only" : "No PDF available"}
        </span>
      </div>
    </article>
  );
}

function App() {
  const desktop = useMemo(() => isDesktopRuntime(), []);
  const [source, setSource] = useState<"mock" | "local">(desktop ? "local" : "mock");
  const [mode, setMode] = useState<SearchMode>("STRICT");
  const [eligibility, setEligibility] = useState("verified-qualified");
  const [query, setQuery] = useState("");
  const [facets, setFacets] = useState<Array<{
    id: string;
    namespace: string;
    tagText: string;
    operator: "ANY" | "ALL" | "NOT";
    tagReviewState: "" | "verified" | "needs-manual-review";
  }>>([]);
  const [searchData, setSearchData] = useState<SearchData>(emptySearch);
  const [health, setHealth] = useState<{ paper_count: number; index_version: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const searchRunId = useRef(0);
  const cardRefs = useRef<(HTMLElement | null)[]>([]);

  const invalidateResults = useCallback(() => {
    searchRunId.current += 1;
    setSearchData(emptySearch);
    setHasSearched(false);
    setSelectedIndex(null);
    setError(null);
    setBusy(false);
  }, []);

  const makeRequest = useCallback((cursor: string | null): SearchRequest => ({
    query: query.trim(),
    mode,
    scope: "LOCAL_ONLY",
    hard_filters: {
      eligibility: [eligibility],
      review_state: ["discovered", "abstract-screened", "fulltext-indexed", "manually-verified"],
      facets: facets.map((facet) => ({
        namespace: facet.namespace.trim(),
        operator: facet.operator,
        tags: facet.tagText.split(",").map((tag) => tag.trim()).filter(Boolean),
        ...(facet.tagReviewState ? { review_state: facet.tagReviewState } : {}),
      })),
      exclude_paper_ids: [],
    },
    limit: 20,
    cursor,
  }), [eligibility, facets, mode, query]);

  useEffect(() => {
    if (!desktop) return;
    let active = true;
    getHealth()
      .then((result) => {
        if (active) {
          setHealth({ paper_count: result.paper_count, index_version: result.index_version });
        }
      })
      .catch((caught) => {
        if (active) {
          setError(displayError(caught));
        }
      });
    return () => {
      active = false;
    };
  }, [desktop]);

  // Keyboard navigation & shortcuts
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      // ⌘K / Ctrl+K focuses and selects search input
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
        inputRef.current?.select();
        setSelectedIndex(null);
        return;
      }

      // Escape key handles hierarchical dismissal:
      // 1. Close filter panel if open
      // 2. Collapse search results if active
      // 3. Hide floating window if on desktop
      if (event.key === "Escape") {
        if (filtersOpen) {
          event.preventDefault();
          setFiltersOpen(false);
          inputRef.current?.focus();
          return;
        }
        if (hasSearched) {
          event.preventDefault();
          invalidateResults();
          inputRef.current?.focus();
          return;
        }
        if (desktop) {
          event.preventDefault();
          try {
            void getCurrentWindow().hide();
          } catch {
            // Non-Tauri environment fallback
          }
          return;
        }
      }

      // Result list navigation with Arrow keys
      if (hasSearched && !filtersOpen && searchData.results.length > 0) {
        if (event.key === "ArrowDown") {
          event.preventDefault();
          setSelectedIndex((prev) => {
            const next = prev === null ? 0 : Math.min(prev + 1, searchData.results.length - 1);
            cardRefs.current[next]?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
            return next;
          });
          return;
        }

        if (event.key === "ArrowUp") {
          event.preventDefault();
          setSelectedIndex((prev) => {
            if (prev === null || prev === 0) {
              inputRef.current?.focus();
              inputRef.current?.select();
              return null;
            }
            const next = prev - 1;
            cardRefs.current[next]?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
            return next;
          });
          return;
        }


        // Enter on a selected result when input is not actively focused
        if (event.key === "Enter" && selectedIndex !== null && document.activeElement !== inputRef.current) {
          const selectedPaper = searchData.results[selectedIndex];
          if (selectedPaper) {
            event.preventDefault();
            if (selectedPaper.source_url && /^https?:\/\//i.test(selectedPaper.source_url)) {
              window.open(selectedPaper.source_url, "_blank", "noreferrer");
            } else {
              const detailsEl = cardRefs.current[selectedIndex]?.querySelector("details");
              if (detailsEl) detailsEl.open = !detailsEl.open;
            }
          }
          return;
        }

        // ⌘C on selected paper when no text is explicitly selected
        if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "c") {
          const selection = window.getSelection();
          if ((!selection || selection.toString().trim() === "") && selectedIndex !== null) {
            const selectedPaper = searchData.results[selectedIndex];
            if (selectedPaper) {
              event.preventDefault();
              void copyToClipboard(formatCitation(selectedPaper));
            }
          }
        }
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [desktop, filtersOpen, hasSearched, invalidateResults, searchData.results, selectedIndex]);

  // Adjust native window height smoothly without jarring recentering
  useEffect(() => {
    if (!desktop) return;
    const win = getCurrentWindow();
    const targetHeight = filtersOpen ? 750 : hasSearched ? 800 : 354;
    void (async () => {
      try {
        await win.setSize(new LogicalSize(900, targetHeight));
      } catch {
        // Layout remains functional when host window controls are restricted.
      }
    })();
  }, [desktop, filtersOpen, hasSearched]);

  const runSearch = async (event?: FormEvent, cursor: string | null = null, eligibilityOverride?: string) => {
    event?.preventDefault();
    const incompleteFacet = facets.some((facet) =>
      !facet.namespace.trim() || !facet.tagText.split(",").some((tag) => tag.trim()),
    );
    if (incompleteFacet) {
      setError("Complete each tag facet or remove it before searching.");
      setHasSearched(false);
      setFiltersOpen(true);
      return;
    }
    setFiltersOpen(false);
    const runId = cursor ? searchRunId.current : ++searchRunId.current;
    setBusy(true);
    setError(null);
    setHasSearched(true);
    setSelectedIndex(null);
    try {
      const request = makeRequest(cursor);
      if (eligibilityOverride) request.hard_filters.eligibility = [eligibilityOverride];
      const response = source === "mock" ? mockSearch(request) : await searchLocal(request);
      if (searchRunId.current !== runId) return;
      setSearchData((current) => cursor
        ? { ...response, results: [...current.results, ...response.results] }
        : response);
    } catch (caught) {
      if (searchRunId.current !== runId) return;
      setError(displayError(caught));
      if (!cursor) setSearchData(emptySearch);
    } finally {
      if (searchRunId.current === runId) setBusy(false);
    }
  };

  const statusText = source === "mock"
    ? "Demo mode · fictional sample records"
    : health
      ? `Local service · ${health.paper_count.toLocaleString()} papers · ${health.index_version}`
      : error
        ? "Local service unavailable"
      : "Local service · checking connection";

  return (
    <main className="launcher-shell">
      <div className="launcher-column">
        <section className="launcher-card" aria-label="ResearchOS quick search">
          {desktop && <div className="drag-region" data-tauri-drag-region aria-label="Drag search window" />}
          {desktop && (
            <button
              className="close-window"
              type="button"
              aria-label="Close window"
              title="Close window (Esc)"
              onClick={() => {
                try {
                  void getCurrentWindow().hide();
                } catch {
                  void getCurrentWindow().close();
                }
              }}
            >
              ×
            </button>
          )}
          <form className="launcher-form" onSubmit={(event) => void runSearch(event)}>
            <label className="sr-only" htmlFor="research-query">Research question or exact method</label>
            <input
              ref={inputRef}
              id="research-query"
              type="search"
              value={query}
              onChange={(event) => { invalidateResults(); setQuery(event.target.value); }}
              placeholder="Search your research library"
              autoComplete="off"
              autoFocus
              onKeyDown={(event) => {
                if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                  event.preventDefault();
                  void runSearch();
                }
              }}
            />
            <div className="launcher-actions">
              <div className="action-group">
                <button
                  className={`action-icon ${filtersOpen ? "is-active" : ""}`}
                  type="button"
                  aria-label="Search options"
                  aria-expanded={filtersOpen}
                  title="Search options"
                  onClick={() => setFiltersOpen((open) => !open)}
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v16M4 12h16" /></svg>
                </button>
                <span className="scope-copy">{source === "mock" ? "Fictional demo" : "Local · private"}</span>
                {facets.length > 0 && <span className="facet-count">{facets.length} tag {facets.length === 1 ? "filter" : "filters"}</span>}
              </div>
              <div className="action-group">
                <button
                  className="mode-button"
                  type="button"
                  aria-label={`Search mode: ${mode === "STRICT" ? "Fast lexical" : "Hybrid"}. Click to switch`}
                  title={mode === "STRICT" ? "Fast strict lexical search" : "Hybrid lexical and available local semantic candidates"}
                  onClick={() => { invalidateResults(); setMode((current) => current === "BROAD" ? "STRICT" : "BROAD"); }}
                >
                  {mode === "STRICT" ? "Fast" : "Hybrid"}
                  <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m6 8 4 4 4-4" /></svg>
                </button>
                <button className="search-button" type="submit" disabled={busy} aria-label={busy ? "Searching" : "Search"} title="Search (Enter)">
                  {busy
                    ? <span className="busy-spinner" aria-hidden="true" />
                    : <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.7" cy="10.7" r="6.7" /><path d="m16 16 5 5" /></svg>}
                </button>
              </div>
            </div>
          </form>
        </section>

        <nav className="launcher-tabs" aria-label="Quick search view">
          <button className={!filtersOpen ? "active" : ""} type="button" aria-pressed={!filtersOpen} onClick={() => { setFiltersOpen(false); inputRef.current?.focus(); }}>Search</button>
          <button className={filtersOpen ? "active" : ""} type="button" aria-pressed={filtersOpen} onClick={() => setFiltersOpen(true)}>Filters</button>
        </nav>
        <div className={`connection ${source === "mock" ? "demo-connection" : ""}`} role="status">
          <span className="status-dot" aria-hidden="true" />{statusText}
          <span className="shortcut-hint">⌘ K</span>
        </div>

        {error && !hasSearched && <div className="error-banner" role="alert">{error}</div>}

        {filtersOpen && (
          <section className="filter-panel" aria-label="Search options">
            <div className="filter-panel-inner">
              <h2>Search options</h2>
              <fieldset className="source-options">
                <legend>Data source</legend>
                <label className="radio-row">
                  <input type="radio" name="source" value="local" checked={source === "local"} onChange={() => { invalidateResults(); setHealth(null); setSource("local"); }} />
                  <span><strong>Local library</strong><small>Search indexed papers on this device</small></span>
                </label>
                <label className="radio-row">
                  <input type="radio" name="source" value="mock" checked={source === "mock"} onChange={() => { invalidateResults(); setHealth(null); setSource("mock"); }} />
                  <span><strong>Demo mock</strong><small>Fictional examples for exploring the interface</small></span>
                </label>
              </fieldset>

              <label className="control-label" htmlFor="search-mode">Search mode</label>
              <select id="search-mode" value={mode} onChange={(event) => { invalidateResults(); setMode(event.target.value as SearchMode); }}>
                <option value="BROAD">Broad · lexical + semantic candidates</option>
                <option value="STRICT">Strict · exact terms and filters</option>
              </select>
              <p className="field-hint">Filters stay exact. An empty intersection stays empty.</p>

              <label className="control-label" htmlFor="eligibility">Publication eligibility</label>
              <select id="eligibility" value={eligibility} onChange={(event) => { invalidateResults(); setEligibility(event.target.value); }}>
                <option value="verified-qualified">Verified qualified · default</option>
                <option value="exploratory">Exploratory · opt in</option>
                <option value="unknown">Unknown · opt in</option>
                <option value="verified-not-qualified">Verified not qualified</option>
              </select>
              <p className="field-hint">Unverified source records remain outside the default qualified results.</p>

              <hr />
              <h3>Tag filter</h3>
              {facets.map((facet, index) => {
                const fieldId = `tag-facet-${index + 1}`;
                const updateFacet = (changes: Partial<typeof facet>) => {
                  invalidateResults();
                  setFacets((current) => current.map((item) => item.id === facet.id ? { ...item, ...changes } : item));
                };
                return (
                  <fieldset className="facet-row" key={facet.id}>
                    <legend>Tag facet {index + 1}</legend>
                    <button className="remove-facet" type="button" aria-label={`Remove tag filter ${index + 1}`} onClick={() => { invalidateResults(); setFacets((current) => current.filter((item) => item.id !== facet.id)); }}>Remove</button>
                    <label className="control-label" htmlFor={`${fieldId}-namespace`}>Namespace</label>
                    <input id={`${fieldId}-namespace`} value={facet.namespace} onChange={(event) => updateFacet({ namespace: event.target.value })} placeholder="e.g. method" />
                    <label className="control-label" htmlFor={`${fieldId}-operator`}>Within this facet</label>
                    <select id={`${fieldId}-operator`} value={facet.operator} onChange={(event) => updateFacet({ operator: event.target.value as typeof facet.operator })}>
                      <option value="ANY">ANY · match one tag</option>
                      <option value="ALL">ALL · match every tag</option>
                      <option value="NOT">NOT · exclude these tags</option>
                    </select>
                    <label className="control-label" htmlFor={`${fieldId}-values`}>Canonical tag IDs</label>
                    <textarea id={`${fieldId}-values`} value={facet.tagText} onChange={(event) => updateFacet({ tagText: event.target.value })} placeholder="flash-attention, gqa" rows={2} />
                    <label className="control-label" htmlFor={`${fieldId}-review`}>Tag review state</label>
                    <select id={`${fieldId}-review`} value={facet.tagReviewState} onChange={(event) => updateFacet({ tagReviewState: event.target.value as typeof facet.tagReviewState })}>
                      <option value="">Any review state</option>
                      <option value="verified">Verified only</option>
                      <option value="needs-manual-review">Needs manual review</option>
                    </select>
                  </fieldset>
                );
              })}
              <button className="add-facet" type="button" onClick={() => { invalidateResults(); setFacets((current) => [...current, { id: crypto.randomUUID(), namespace: "", tagText: "", operator: "ANY", tagReviewState: "" }]); }}>+ Add tag facet</button>
              <p className="field-hint">Use canonical tag IDs. Facets combine with AND; operators apply within each facet.</p>
            </div>
            <div className="filter-bar">
              <span>Changing filters clears stale results. Search again to apply.</span>
              <button type="button" onClick={() => { setFiltersOpen(false); inputRef.current?.focus(); }}>Done</button>
            </div>
          </section>
        )}

        {hasSearched && !filtersOpen && (
          <section className="results-panel" aria-labelledby="results-title">
            <div className="result-heading">
              <div>
                <p className="eyebrow">{source === "mock" ? "FICTIONAL DEMO" : "ON-DEVICE PAPER SEARCH"}</p>
                <h2 id="results-title">{busy ? "Searching…" : `${searchData.total} ${searchData.total === 1 ? "result" : "results"}`}</h2>
              </div>
              <div className="result-controls">
                <span>{eligibility === "verified-qualified" ? "Verified only" : `Eligibility: ${eligibility}`}</span>
                <button type="button" aria-label="Collapse results" title="Collapse results (Esc)" onClick={() => invalidateResults()}>×</button>
              </div>
            </div>
            {error && <div className="error-banner" role="alert"><strong>Search unavailable</strong><span>{error}</span></div>}
            {source === "local" && !desktop && <div className="empty-state"><h3>Open the desktop app to search locally</h3><p>The browser preview cannot access your private on-device index. Sample papers are never mixed into local results.</p></div>}
            {hasSearched && !error && searchData.warnings.map((warning) => <p className="warning-note" key={warning}>{warning}</p>)}
            {!busy && !error && searchData.results.length === 0 && !(source === "local" && !desktop) && (
              <div className="empty-state">
                <h3>No papers matched these constraints</h3>
                <p>Exact eligibility and tag filters were preserved. {eligibility === "verified-qualified" ? "Your imported papers may still need eligibility review." : "Try a different query or adjust filters."}</p>
                {eligibility === "verified-qualified"
                  ? <button type="button" onClick={() => { setEligibility("unknown"); void runSearch(undefined, null, "unknown"); }}>Search unknown candidates instead</button>
                  : <button type="button" onClick={() => setFiltersOpen(true)}>Review filters</button>}
              </div>
            )}
            <div className="paper-list" aria-live="polite" aria-busy={busy}>
              {searchData.results.map((paper, index) => (
                <PaperCard
                  key={paper.paper_id}
                  paper={paper}
                  isSelected={selectedIndex === index}
                  onSelect={() => setSelectedIndex(index)}
                  cardRef={(el) => { cardRefs.current[index] = el; }}
                />
              ))}
            </div>
            {searchData.next_cursor && <button className="more-button" disabled={busy} onClick={() => void runSearch(undefined, searchData.next_cursor)}>Load more results</button>}
            <footer className="results-footer">{source === "mock" ? "These are fictional UI fixtures, not scholarly evidence." : `Index: ${searchData.index_version} · Dense: ${searchData.dense_status} · Search remains local`}</footer>
          </section>
        )}
      </div>
    </main>
  );
}

export default App;

