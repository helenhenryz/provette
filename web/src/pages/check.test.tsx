/* The check composer takes a dropped file: a .py into the protocol, a .json into the plate
   map, anything else named and left alone; the file inputs behind the buttons do the same.
   The composer's draft and the last check's id live for the tab's session (sessionStorage):
   a draft survives a remount, the Check tab comes back to the last result, /check?new is the
   composer, and posting a check remembers its id and drops the draft. */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
  useParams,
} from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CheckPage } from "./Check";

const lastChecks: {
  checks: {
    id: string;
    name: string;
    created: number;
    simulator: string;
    findings: number;
    has_map: boolean;
  }[];
} = { checks: [] };
const { create } = vi.hoisted(() => ({
  create: vi.fn(() => Promise.resolve({ id: "new1" })),
}));

vi.mock("../lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("../lib/api")>();
  return {
    ...real,
    checks: {
      platemaps: () => Promise.resolve({ platemaps: [] }),
      list: () => Promise.resolve(lastChecks),
      example: vi.fn(),
      platemap: vi.fn(),
      create,
    },
  };
});

const PROTOCOL =
  "from opentrons import protocol_api\n\ndef run(protocol):\n    pass\n";
const MAP = '{"id": "pcr-01", "liquids": [], "variants": []}';

function page() {
  return render(
    <MemoryRouter>
      <CheckPage />
    </MemoryRouter>,
  );
}

function Result() {
  const { id } = useParams();
  return <div>result {id}</div>;
}

function Where() {
  const at = useLocation();
  return <div data-testid="where">{at.pathname + at.search}</div>;
}

/* The routes the page lives among: /check (the page), /check/:id (a stand-in result). */
function routed(at: string) {
  return render(
    <MemoryRouter initialEntries={[at]}>
      <Routes>
        <Route
          path="/check"
          element={
            <>
              <CheckPage />
              <Where />
            </>
          }
        />
        <Route path="/check/:id" element={<Result />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CheckPage", () => {
  // a file drop is read asynchronously, so a draft may be saved after the last test's cleanup
  beforeEach(() => sessionStorage.clear());
  afterEach(() => {
    sessionStorage.clear();
    create.mockClear();
  });

  it("takes a dropped .py as the protocol and a .json as the plate map", async () => {
    page();
    const zone = screen.getByTestId("composer");
    fireEvent.drop(zone, {
      dataTransfer: {
        files: [new File([PROTOCOL], "mine.py", { type: "text/x-python" })],
      },
    });
    await waitFor(() =>
      expect(screen.getByLabelText(/^Protocol \(\.py\)/)).toHaveValue(PROTOCOL),
    );
    expect(screen.getByText("mine.py")).toBeInTheDocument();
    // the map dropped after it: the paste choice is picked and filled
    fireEvent.drop(zone, {
      dataTransfer: {
        files: [new File([MAP], "map.json", { type: "application/json" })],
      },
    });
    await waitFor(() =>
      expect(
        screen.getByRole("radio", { name: /Paste or upload JSON/ }),
      ).toBeChecked(),
    );
    expect(screen.getByPlaceholderText(/"variants"/)).toHaveValue(MAP);
    expect(screen.getByLabelText(/^Protocol \(\.py\)/)).toHaveValue(PROTOCOL); // untouched by the second drop
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("says in a sentence what a drop of anything else was, and leaves the fields alone", async () => {
    page();
    fireEvent.drop(screen.getByTestId("composer"), {
      dataTransfer: {
        files: [new File(["notes"], "bench.txt", { type: "text/plain" })],
      },
    });
    expect(await screen.findByRole("status")).toHaveTextContent(
      "bench.txt: not a .py protocol or a .json plate map, so it was left alone.",
    );
    expect(screen.getByLabelText(/^Protocol \(\.py\)/)).toHaveValue("");
  });

  it("refuses a .py that is not an Opentrons protocol, and leaves the protocol field alone", async () => {
    page();
    fireEvent.drop(screen.getByTestId("composer"), {
      dataTransfer: {
        files: [
          new File(["print('hello')\n"], "script.py", {
            type: "text/x-python",
          }),
        ],
      },
    });
    expect(await screen.findByRole("status")).toHaveTextContent(
      "script.py: not an Opentrons protocol (no run(protocol) function), so it was not added.",
    );
    expect(screen.getByLabelText(/^Protocol \(\.py\)/)).toHaveValue("");
  });

  it("still takes a file from the input behind the button", async () => {
    page();
    expect(
      screen.getByRole("button", { name: "Choose a file" }),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("The protocol file"), {
      target: { files: [new File([PROTOCOL], "chosen.py")] },
    });
    await waitFor(() =>
      expect(screen.getByLabelText(/^Protocol \(\.py\)/)).toHaveValue(PROTOCOL),
    );
    expect(screen.getByText("chosen.py")).toBeInTheDocument();
  });

  it("keeps a half-typed draft across a remount, in the tab's session", async () => {
    const first = page();
    fireEvent.change(screen.getByLabelText(/^Protocol \(\.py\)/), {
      target: { value: PROTOCOL },
    });
    fireEvent.drop(screen.getByTestId("composer"), {
      dataTransfer: {
        files: [new File([MAP], "map.json", { type: "application/json" })],
      },
    });
    await waitFor(() =>
      expect(screen.getByPlaceholderText(/"variants"/)).toHaveValue(MAP),
    );
    first.unmount();
    page();
    expect(screen.getByLabelText(/^Protocol \(\.py\)/)).toHaveValue(PROTOCOL);
    expect(
      screen.getByRole("radio", { name: /Paste or upload JSON/ }),
    ).toBeChecked();
    expect(screen.getByPlaceholderText(/"variants"/)).toHaveValue(MAP);
    expect(localStorage.length).toBe(0);
  });

  it("opens the last check when one is remembered; /check?new is the composer", async () => {
    sessionStorage.setItem("provette.check.last", "abc123");
    const remembered = routed("/check");
    expect(await screen.findByText("result abc123")).toBeInTheDocument();
    expect(screen.queryByTestId("composer")).toBeNull();
    remembered.unmount();
    routed("/check?new");
    expect(screen.getByTestId("composer")).toBeInTheDocument();
    expect(screen.getByTestId("where")).toHaveTextContent("/check?new");
  });

  it("remembers a posted check's id and drops the draft", async () => {
    routed("/check");
    fireEvent.change(screen.getByLabelText(/^Protocol \(\.py\)/), {
      target: { value: PROTOCOL },
    });
    expect(
      JSON.parse(sessionStorage.getItem("provette.check.draft") ?? "{}"),
    ).toMatchObject({ protocol: PROTOCOL });
    fireEvent.click(screen.getByRole("button", { name: "Check the protocol" }));
    expect(await screen.findByText("result new1")).toBeInTheDocument();
    expect(create).toHaveBeenCalledWith({
      protocol: PROTOCOL,
      platemap: null,
      name: "protocol.py",
    });
    expect(sessionStorage.getItem("provette.check.last")).toBe("new1");
    expect(sessionStorage.getItem("provette.check.draft")).toBeNull();
  });
});
