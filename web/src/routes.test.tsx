/* The pages and their addresses: /, /examples, /check, /rules, /methods, /about and the records;
   any other address is the not-found page. */

import { act, render, screen } from "@testing-library/react";
import { useState } from "react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { PerRecord, routes } from "./routes";

vi.mock("./lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("./lib/api")>();
  return {
    ...real,
    api: {
      ...real.api,
      health: () =>
        Promise.resolve({
          ok: true,
          opentrons: "8.8.2",
          provette: "0",
          episodes: 0,
          live: false,
        }),
    },
  };
});
vi.mock("./replay/Deck3D", () => ({ Deck3D: () => null }));

const paths = () => routes()[0].children!.map((r) => r.path);

describe("routes", () => {
  it("has one plain address per page, and nothing else", () => {
    expect(paths()).toEqual([
      undefined,
      "examples",
      "plan/:id",
      "runs/:id",
      "episodes/:set/:condition/:requestId",
      "check",
      "check/:id",
      "methods",
      "rules",
      "rules/new",
      "docs/:name",
      "about",
      "*",
    ]);
  });

  it("answers any other address with the not-found page", async () => {
    render(
      <RouterProvider
        router={createMemoryRouter(routes(), { initialEntries: ["/knows"] })}
      />,
    );
    expect(
      await screen.findByRole("heading", {
        name: "There is nothing at this address.",
      }),
    ).toBeInTheDocument();
  });
});

describe("PerRecord", () => {
  it("starts a record's page afresh when History moves to another record on the same route", () => {
    let mounts = 0;
    function Page() {
      const [n] = useState(() => ++mounts);
      return <p>mount {n}</p>;
    }
    const router = createMemoryRouter(
      [
        {
          path: "/runs/:id",
          element: (
            <PerRecord>
              <Page />
            </PerRecord>
          ),
        },
      ],
      { initialEntries: ["/runs/a"] },
    );
    render(<RouterProvider router={router} />);
    expect(screen.getByText("mount 1")).toBeInTheDocument();
    act(() => void router.navigate("/runs/b"));
    expect(screen.getByText("mount 2")).toBeInTheDocument();
  });
});
