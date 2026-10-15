import type { SearchData, SearchRequest, SearchResult } from "./contracts";

// These fixtures are invented display examples. They are confined to the explicit
// demo source and are never mixed with responses from the local service.
const demoResults: SearchResult[] = [
  {
    paper_id: "DEMO-001",
    title: "Efficient Attention for Long-Context Language Models",
    abstract:
      "Demonstration record only. This mock card shows how an abstract-only local result will be presented.",
    authors: ["Demo Author"],
    year: 2024,
    doi: null,
    source_url: null,
    review_state: "abstract-screened",
    eligibility: "exploratory",
    tags: [
      { tag_id: "method/efficient-attention", review_state: "needs-manual-review", role: "candidate" },
    ],
    pdf_state: "UNAVAILABLE",
    match_routes: ["EXACT_TERM", "TAG_CANDIDATE"],
    score: 0.82,
  },
  {
    paper_id: "DEMO-002",
    title: "Personalized Federated Learning with Client-Level Attention",
    abstract:
      "Demonstration record only. No publication or method claims are verified by this sample.",
    authors: ["Example Research Group"],
    year: 2023,
    doi: null,
    source_url: null,
    review_state: "discovered",
    eligibility: "exploratory",
    tags: [
      { tag_id: "method/attention", review_state: "needs-manual-review", role: "candidate" },
      { tag_id: "field/federated-learning", review_state: "needs-manual-review", role: "candidate" },
    ],
    pdf_state: "REMOTE_ONLY",
    match_routes: ["SEMANTIC", "TAG_CANDIDATE"],
    score: 0.71,
  },
];

export function mockSearch(request: SearchRequest): SearchData {
  const normalized = request.query.trim().toLowerCase();
  const results = normalized
    ? demoResults.filter((paper) =>
        `${paper.title} ${paper.abstract}`.toLowerCase().includes(normalized),
      )
    : demoResults;
  return {
    results: results.slice(0, request.limit),
    total: results.length,
    next_cursor: null,
    index_version: "MOCK-ONLY",
    dense_status: "unavailable",
    warnings: ["Demo records are fictional UI fixtures, not local library search results."],
  };
}
