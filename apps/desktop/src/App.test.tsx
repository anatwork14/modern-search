import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import App from "./App";

afterEach(cleanup);

describe("ResearchOS desktop search shell", () => {
  it("labels the demo source and only shows fictional examples after a search", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(screen.getByRole("status")).toHaveTextContent("Demo mode · fictional sample records");
    expect(screen.queryByText("DEMO-001")).not.toBeInTheDocument();

    await user.type(screen.getByRole("searchbox", { name: /research question or exact method/i }), "attention");
    await user.keyboard("{Enter}");

    expect(await screen.findByText("DEMO-001")).toBeInTheDocument();
    expect(screen.getByText(/fictional UI fixtures/i)).toBeInTheDocument();
    expect(screen.getByText("No PDF available")).toBeInTheDocument();
  });

  it("keeps local library empty state distinct from demo records", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("radio", { name: /local library/i }));
    expect(await screen.findByText("Open the desktop app to search locally")).toBeInTheDocument();
    expect(screen.queryByText("DEMO-001")).not.toBeInTheDocument();
  });

  it("supports repeatable facet rows and clears stale result cards when filters change", async () => {
    const user = userEvent.setup();
    render(<App />);

    const query = screen.getByRole("searchbox", { name: /research question or exact method/i });
    await user.type(query, "attention");
    await user.keyboard("{Enter}");
    expect(await screen.findByText("DEMO-001")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /add tag facet/i }));
    expect(screen.queryByText("DEMO-001")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Your results" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /add tag facet/i }));
    expect(screen.getAllByLabelText("Namespace")).toHaveLength(2);
    expect(screen.getAllByLabelText("Within this facet")).toHaveLength(2);
  });
});
