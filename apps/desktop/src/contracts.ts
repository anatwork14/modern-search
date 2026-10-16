export type SearchMode = "STRICT" | "BROAD";
export type ReviewState =
  | "discovered"
  | "abstract-screened"
  | "fulltext-indexed"
  | "manually-verified"
  | "experiment-reproduced";
export type PdfState = "REMOTE_ONLY" | "UNAVAILABLE" | "VERIFIED_LOCAL";
export type MatchRoute =
  | "EXACT_TERM"
  | "TAG_VERIFIED"
  | "TAG_CANDIDATE"
  | "SEMANTIC"
  | "GRAPH_NEIGHBOR"
  | "CROSS_DOMAIN_ANALOGY";

export interface Facet {
  namespace: string;
  operator: "ANY" | "ALL" | "NOT";
  tags: string[];
  review_state?: "verified" | "needs-manual-review";
}

export interface SearchRequest {
  query: string;
  mode: SearchMode;
  scope: "LOCAL_ONLY";
  hard_filters: {
    eligibility: string[];
    review_state: ReviewState[];
    facets: Facet[];
    exclude_paper_ids: string[];
  };
  limit: number;
  cursor: string | null;
}

export interface PaperTag {
  tag_id: string;
  review_state: "needs-manual-review" | "verified" | "rejected";
  role: string;
}

export interface VenueEvidence {
  venue_type?: string | null;
  core_rank?: string | null;
  sjr_quartile?: string | null;
  ranking_system?: string | null;
  ranking_year?: number | null;
  ranking_category?: string | null;
  ranking_source_url?: string | null;
  publication_evidence_url?: string | null;
}

export interface SearchResult {
  paper_id: string;
  title: string;
  abstract: string | null;
  authors: string[];
  year: number | null;
  doi: string | null;
  source_url: string | null;
  venue?: string | null;
  venue_evidence?: VenueEvidence[];
  review_state: ReviewState;
  eligibility: string;
  tags: PaperTag[];
  pdf_state: PdfState;
  match_routes: MatchRoute[];
  score: number;
}

export interface SearchData {
  results: SearchResult[];
  total: number;
  next_cursor: string | null;
  index_version: string;
  dense_status: "unavailable" | "ready";
  warnings: string[];
}

export interface HealthData {
  status: string;
  offline: boolean;
  dense_status: "unavailable" | "ready";
  index_version: string;
  paper_count: number;
  capabilities?: string[];
  fulltext_page_evidence?: boolean;
}

export interface TaxonomyTag {
  tag_id: string;
  namespace: string;
  label: string;
  aliases: string[];
}

export type RpcErrorCode =
  | "INVALID_REQUEST"
  | "MODEL_UNAVAILABLE"
  | "INDEX_MISMATCH"
  | "INTERNAL_ERROR";

export interface RpcError {
  code: RpcErrorCode;
  message: string;
}
