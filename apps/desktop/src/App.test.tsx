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
    expect(within(screen.getByRole("region", { name: /researchos quick search/i })).getByRole("button", { name: "Search" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /search mode: broad/i })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Demo mode · fictional sample records");
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
    await user.click(screen.getByRole("button", { name: /search mode: broad/i }));
    expect(screen.getByRole("button", { name: /search mode: strict/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Filters" }));
    expect(screen.getByLabelText("Publication eligibility")).toHaveValue("verified-qualified");
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
});
