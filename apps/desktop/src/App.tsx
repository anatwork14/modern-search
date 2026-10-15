import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
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

function PaperCard({ paper }: { paper: SearchResult }) {
  const verifiedTags = paper.tags.filter((tag) => tag.review_state === "verified");
  const candidateTags = paper.tags.filter((tag) => tag.review_state === "needs-manual-review");

  return (
    <article className="paper-card">
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
      </p>
      <p className="paper-abstract">{paper.abstract ?? "No abstract is available in the local index."}</p>
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
      <div className="paper-footer">
        <span>{paper.pdf_state === "VERIFIED_LOCAL" ? "Verified local PDF" : paper.pdf_state === "REMOTE_ONLY" ? "Remote PDF link only" : "No PDF available"}</span>
        {paper.source_url && /^https?:\/\//i.test(paper.source_url) && (
          <a href={paper.source_url} target="_blank" rel="noreferrer">Open source</a>
        )}
      </div>
    </article>
  );
}

function App() {
  const desktop = useMemo(() => isDesktopRuntime(), []);
  const [source, setSource] = useState<"mock" | "local">(desktop ? "local" : "mock");
  const [mode, setMode] = useState<SearchMode>("BROAD");
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
  const searchRunId = useRef(0);

  const invalidateResults = useCallback(() => {
    searchRunId.current += 1;
    setSearchData(emptySearch);
    setHasSearched(false);
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

  const checkHealth = useCallback(async () => {
    if (!desktop) return;
    try {
      const result = await getHealth();
      setHealth({ paper_count: result.paper_count, index_version: result.index_version });
    } catch (caught) {
      setError(displayError(caught));
    }
  }, [desktop]);

  useEffect(() => { void checkHealth(); }, [checkHealth]);

  const runSearch = async (event?: FormEvent, cursor: string | null = null) => {
    event?.preventDefault();
    const incompleteFacet = facets.some((facet) =>
      !facet.namespace.trim() || !facet.tagText.split(",").some((tag) => tag.trim()),
    );
    if (incompleteFacet) {
      setError("Complete each tag facet or remove it before searching.");
      setHasSearched(false);
      return;
    }
    const runId = cursor ? searchRunId.current : ++searchRunId.current;
    setBusy(true);
    setError(null);
    setHasSearched(true);
    try {
      const request = makeRequest(cursor);
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
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#main" aria-label="ResearchOS home">
          <span className="brand-mark" aria-hidden="true">R</span>
          <span><strong>ResearchOS</strong><small>Local research library</small></span>
        </a>
        <div className={`connection ${source === "mock" ? "demo-connection" : "local-connection"}`} role="status">
          <span className="status-dot" aria-hidden="true" />{statusText}
        </div>
      </header>

      <section className="intro" aria-labelledby="page-title">
        <p className="eyebrow">PAPER DISCOVERY WORKSPACE</p>
        <h1 id="page-title">Find the work behind your next idea.</h1>
        <p className="intro-copy">Search your local research library with exact terms and strict, reviewable filters.</p>
      </section>

      <div className="workspace" id="main">
        <aside className="filter-panel" aria-label="Search options">
          <h2>Search setup</h2>
          <fieldset className="source-options">
            <legend>Data source</legend>
            <label className="radio-row">
              <input type="radio" name="source" value="local" checked={source === "local"} onChange={() => { invalidateResults(); setHealth(null); setSource("local"); void checkHealth(); }} />
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
        </aside>

        <section className="results-panel" aria-labelledby="results-title">
          <form className="search-form" onSubmit={(event) => void runSearch(event)}>
            <label htmlFor="research-query">Research question or exact method</label>
            <div className="query-row">
              <input
                id="research-query"
                type="search"
                value={query}
                onChange={(event) => { invalidateResults(); setQuery(event.target.value); }}
                onKeyDown={(event) => {
                  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") void runSearch();
                }}
                placeholder="Try “attention for LLM inference” or “FedAMP”"
                autoFocus
              />
              <button className="search-button" type="submit" disabled={busy}>
                {busy ? "Searching…" : "Search"}<span aria-hidden="true">⌕</span>
              </button>
            </div>
            <div className="search-note"><span>⌘ ↵</span> Search stays on this device</div>
          </form>

          <div className="result-heading">
            <div><p className="eyebrow">LOCAL SEARCH</p><h2 id="results-title">{hasSearched ? `${searchData.total} ${searchData.total === 1 ? "result" : "results"}` : "Your results"}</h2></div>
            <div className="index-summary" aria-label="Index availability">
              <span>Index <b>{source === "mock" ? "DEMO" : health?.index_version ?? "checking"}</b></span>
              <span>Dense search <b>{source === "mock" ? "demo only" : searchData.dense_status}</b></span>
            </div>
          </div>

          {error && <div className="error-banner" role="alert"><strong>Search unavailable</strong><span>{error}</span></div>}
          {source === "local" && !desktop && <div className="empty-state"><span className="empty-icon" aria-hidden="true">⌁</span><h3>Open the desktop app to search locally</h3><p>The browser preview has no access to your on-device service. Demo records stay separate from the local library.</p></div>}
          {source === "local" && desktop && !health && !error && <div className="empty-state"><span className="empty-icon" aria-hidden="true">⌁</span><h3>Connecting to your local index</h3><p>Search will use the on-device service. The renderer cannot choose its executable or database path.</p></div>}
          {source === "local" && health?.paper_count === 0 && !hasSearched && <div className="empty-state"><span className="empty-icon" aria-hidden="true">⌕</span><h3>Your local index is empty</h3><p>Once the catalog has been imported, search results will appear here. No sample records are shown as library data.</p></div>}
          {hasSearched && !error && searchData.warnings.map((warning) => <p className="warning-note" key={warning}>{warning}</p>)}
          {hasSearched && !error && searchData.results.length === 0 && <div className="empty-state"><span className="empty-icon" aria-hidden="true">∅</span><h3>No papers matched these constraints</h3><p>Strict filters are preserved. Review your tags or deliberately change the query and filters.</p></div>}
          <div className="paper-list" aria-live="polite">
            {searchData.results.map((paper) => <PaperCard key={paper.paper_id} paper={paper} />)}
          </div>
          {searchData.next_cursor && <button className="more-button" disabled={busy} onClick={() => void runSearch(undefined, searchData.next_cursor)}>Load more local results</button>}
          <footer className="results-footer">{source === "mock" ? "Demo results are fictional and are never saved to your library." : `Indexed in ${searchData.index_version || health?.index_version || "your local database"} · Dense route: ${searchData.dense_status}`}</footer>
        </section>
      </div>
    </main>
  );
}

export default App;
