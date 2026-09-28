/* The check result: "Check another" in the header reaches the composer and clears nothing; a
   remembered check that 404s (another deployment, cleaned data) falls through to the composer
   silently and is forgotten; any other 404 is the "No such check" notice. */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, type CheckRow } from "../lib/api";
import { analysis } from "../test/fixtures";
import { CheckResultPage } from "./CheckResult";

const row: CheckRow = {
  id: "abc",
  name: "mine.py",
  created: 1,
  analysis,
  protocol: analysis.protocol,
  platemap: null,
};
const { get } = vi.hoisted(() => ({
  get: vi.fn<(id: string) => Promise<unknown>>(),
}));
vi.mock("../lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("../lib/api")>();
  return { ...real, checks: { ...real.checks, get } };
});
vi.mock("../replay/Deck3D", () => ({
  Deck3D: () => <div data-testid="deck3d">3D</div>,
}));

function Composer() {
  const at = useLocation();
  return <div data-testid="composer">{at.pathname + at.search}</div>;
}

function page(at: string) {
  return render(
    <MemoryRouter initialEntries={[at]}>
      <Routes>
        <Route path="/check" element={<Composer />} />
        <Route path="/check/:id" element={<CheckResultPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CheckResultPage", () => {
  afterEach(() => {
    sessionStorage.clear();
    get.mockReset();
  });

  it("offers Check another in the header, which reaches the composer and forgets nothing", async () => {
    get.mockResolvedValue(row);
    sessionStorage.setItem("provette.check.last", "abc");
    sessionStorage.setItem("provette.check.draft", '{"protocol":"x"}');
    page("/check/abc");
    const another = await screen.findByRole("link", { name: "Check another" });
    expect(another).toHaveAttribute("href", "/check?new");
    await userEvent.setup().click(another);
    expect(await screen.findByTestId("composer")).toHaveTextContent(
      "/check?new",
    );
    expect(sessionStorage.getItem("provette.check.last")).toBe("abc");
    expect(sessionStorage.getItem("provette.check.draft")).toBe(
      '{"protocol":"x"}',
    );
  });

  it("falls through to the composer when the remembered check is gone, and forgets it", async () => {
    get.mockRejectedValue(new ApiError(404, "No such check"));
    sessionStorage.setItem("provette.check.last", "gone");
    page("/check/gone");
    expect(await screen.findByTestId("composer")).toHaveTextContent("/check");
    await waitFor(() =>
      expect(sessionStorage.getItem("provette.check.last")).toBeNull(),
    );
    expect(screen.queryByText("No such check")).toBeNull();
  });

  it("says No such check for a 404 that is not the remembered one", async () => {
    get.mockRejectedValue(new ApiError(404, "No such check"));
    sessionStorage.setItem("provette.check.last", "other");
    page("/check/gone");
    expect(await screen.findByText("No such check")).toBeInTheDocument();
    expect(sessionStorage.getItem("provette.check.last")).toBe("other");
    expect(screen.queryByTestId("composer")).toBeNull();
  });
});
