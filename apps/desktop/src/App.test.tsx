import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import App from "./App";

afterEach(cleanup);

describe("ResearchOS quick-search launcher", () => {
  it("starts with a compact search-first surface and accessible controls", () => {
    render(<App />);
    expect(screen.getByRole("region", { name: /researchos quick search/i })).toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: /research question or exact method/i })).toBeInTheDocument();
    const searchForm = screen.getByRole("searchbox").closest("form");
    expect(within(searchForm!).getByRole("button", { name: "Search" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /search mode: fast lexical/i })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Demo mode · fictional sample records");
    const card = screen.getByRole("region", { name: /researchos quick search/i });
    expect(card).toContainElement(screen.getByRole("navigation", { name: /quick search view/i }));
    expect(card).toContainElement(screen.getByRole("status"));
    expect(screen.queryByRole("heading", { name: "Your results" })).not.toBeInTheDocument();
    expect(screen.queryByText("DEMO-001")).not.toBeInTheDocument();
  });

  it("searches fictional demo records, while evidence stays transparent", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByRole("searchbox"), "attention{Enter}");
    const paper = await screen.findByText("DEMO-001");
    const card = paper.closest("article");
    expect(card).not.toBeNull();
    expect(screen.getAllByText(/fictional UI fixtures/i)).toHaveLength(2);
    expect(within(card!).getByText("No PDF available")).toBeInTheDocument();
    expect(within(card!).getByText("Source-reported venue evidence")).toBeInTheDocument();
    await user.click(within(card!).getByText("Evidence & tags"));
    expect(within(card!).getByText("Ranking year: 2023")).toBeInTheDocument();
    expect(within(card!).getByRole("link", { name: "Ranking source" })).toHaveAttribute("href", "https://example.com/demo-ranking");
  });

  it("keeps the browser demo separate from local library results", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Search options" }));
    await user.click(screen.getByRole("radio", { name: /local library/i }));
    await user.click(screen.getByRole("button", { name: "Done" }));
    await user.type(screen.getByRole("searchbox"), "attention{Enter}");
    expect(await screen.findByText("Open the desktop app to search locally")).toBeInTheDocument();
    expect(screen.queryByText("DEMO-001")).not.toBeInTheDocument();
  });

  it("keeps advanced facet controls off the default surface and clears stale results when changed", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByRole("searchbox"), "attention{Enter}");
    expect(await screen.findByText("DEMO-001")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Search options" }));
    expect(screen.queryByText("DEMO-001")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /add tag facet/i }));
    expect(screen.queryByText("DEMO-001")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /add tag facet/i }));
    expect(screen.getAllByLabelText("Namespace")).toHaveLength(2);
    expect(screen.getAllByLabelText("Within this facet")).toHaveLength(2);
  });

  it("switches retrieval mode without silently broadening eligibility", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: /search mode: fast lexical/i }));
    expect(screen.getByRole("button", { name: /search mode: hybrid/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Filters" }));
    expect(screen.getByRole("region", { name: /researchos quick search/i }))
      .toContainElement(screen.getByRole("region", { name: /search options/i }));
    expect(screen.getByLabelText("Publication eligibility")).toHaveValue("verified-qualified");
    expect(screen.getByLabelText("Search mode")).toHaveValue("BROAD");
  });

  it("requires explicit scope selection even when a fictional demo search has no matches", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByRole("searchbox"), "no-fictional-paper-with-this-id{Enter}");
    expect(await screen.findByText("No papers matched these constraints")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Search unknown candidates instead" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Review filters" }));
    expect(screen.getByLabelText("Publication eligibility")).toHaveValue("verified-qualified");
    await user.selectOptions(screen.getByLabelText("Publication eligibility"), "unknown");
    expect(screen.getByLabelText("Publication eligibility")).toHaveValue("unknown");
    expect(screen.getByLabelText("Search mode")).toHaveValue("STRICT");
  });

  it("offers concrete keyword refinement for unmatched multiword searches", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByRole("searchbox"), "unmatched attention{Enter}");
    expect(await screen.findByText("No papers matched these constraints")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "attention" }));
    expect(await screen.findByText("DEMO-001")).toBeInTheDocument();
    expect(screen.getByRole("searchbox")).toHaveValue("attention");
  });

  it("supports keyboard focus and closing advanced options", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Filters" }));
    await user.keyboard("{Escape}");
    expect(screen.queryByLabelText("Publication eligibility")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Filters" }));
    await user.keyboard("{Control>}k{/Control}");
    expect(screen.getByRole("searchbox")).toHaveFocus();
  });

  it("navigates results with arrow keys and dismisses with Escape", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByRole("searchbox"), "attention{Enter}");
    const firstPaper = await screen.findByText("DEMO-001");
    expect(screen.getByRole("region", { name: /researchos quick search/i }))
      .toContainElement(screen.getByRole("region", { name: /on-device paper search|results/i }));
    const firstCard = firstPaper.closest("article")!;
    expect(firstCard).toBeInTheDocument();

    // Arrow down selects first result
    await user.keyboard("{ArrowDown}");
    expect(firstCard).toHaveAttribute("aria-selected", "true");

    // Arrow down selects second result if present
    await user.keyboard("{ArrowDown}");

    // Escape collapses results and refocuses search input
    await user.keyboard("{Escape}");
    expect(screen.queryByText("DEMO-001")).not.toBeInTheDocument();
    expect(screen.getByRole("searchbox")).toHaveFocus();
  });

  it("provides copy buttons for citation and title", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByRole("searchbox"), "attention{Enter}");
    await screen.findByText("DEMO-001");

    const copyCiteBtn = screen.getAllByRole("button", { name: /copy citation/i })[0];
    expect(copyCiteBtn).toBeInTheDocument();

    const copyTitleBtn = screen.getAllByRole("button", { name: /copy title/i })[0];
    expect(copyTitleBtn).toBeInTheDocument();

    await user.click(copyCiteBtn);
    expect(await screen.findByText("✓ Citation copied")).toBeInTheDocument();
  });
});

