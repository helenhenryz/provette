/* Examples on the frozen evaluation cards: the agent runs, the request as written, one card a
   request with a row per model (Super, then Nano best of 3); a harder request carries a tag;
   no statistics, no set chips, no second wording and no live runs on this page. */

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { episodes } from "../test/fixtures";
import { GalleryPage } from "./Gallery";

vi.mock("../lib/api", () => ({
  api: { episodes: () => Promise.resolve(episodes) },
}));

function page() {
  return render(
    <MemoryRouter>
      <GalleryPage />
    </MemoryRouter>,
  );
}

const plain = episodes.episodes.filter((e) => e.condition === "plain");
const requests = new Set(plain.map((e) => `${e.request_id}|${e.request}`)).size;

describe("GalleryPage (Examples)", () => {
  it("shows every current request once, as written, with its runs as rows", async () => {
    page();
    expect(
      await screen.findByRole("heading", { name: "Examples" }),
    ).toBeInTheDocument();
    const chips = screen.getByRole("group", { name: "Technique" });
    expect(within(chips).getAllByRole("button")[0]).toHaveTextContent(
      `All${requests}`,
    ); // the count is on the All chip
    expect(screen.queryByText(/^\d+ requests?$/)).toBeNull();
    expect(screen.queryByText(/, few tips/)).toBeNull(); // the second wording is not an example
    expect(screen.queryByText(/of 34/)).toBeNull(); // the numbers are on Methods
    expect(screen.queryByRole("button", { name: /^original/ })).toBeNull();
    expect(screen.getAllByText("Nano, best of 3").length).toBeGreaterThan(0);
  });

  it("tags the harder requests and filters by technique", async () => {
    page();
    await screen.findByRole("heading", { name: "Examples" });
    const harder = new Set(
      plain
        .filter((e) => e.request_id.startsWith("hard-"))
        .map((e) => e.request_id),
    ).size;
    expect(screen.getAllByText("harder")).toHaveLength(harder);
    const group = screen.getByRole("group", { name: "Technique" });
    const first = within(group).getAllByRole("button")[1];
    await userEvent.click(first);
    const shown = Number(/\d+$/.exec(first.textContent ?? "")?.[0]);
    expect(shown).toBeLessThan(requests);
    expect(
      screen
        .getAllByRole("link")
        .filter((a) => a.getAttribute("href")?.startsWith("/episodes/")).length,
    ).toBeGreaterThan(0);
  });
});
