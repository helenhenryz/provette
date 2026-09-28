/* Settings: the theme is this browser's; the budgets come from the API with their defaults and
   ranges, a value out of range cannot be saved, Save sends only what changed, and Reset brings
   the defaults back. */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { RunSetting } from "../lib/api";
import { Settings } from "./Settings";

const rows: RunSetting[] = [
  {
    key: "run_tool_calls",
    group: "Runs",
    label: "Tool calls per run",
    words: "w",
    value: 25,
    default: 25,
    low: 5,
    high: 60,
  },
  {
    key: "plan_tokens",
    group: "Plans",
    label: "Tokens per plan",
    words: "w",
    value: 40000,
    default: 40000,
    low: 10000,
    high: 100000,
  },
];
const { saved, reset } = vi.hoisted(() => ({
  saved: [] as Record<string, number>[],
  reset: vi.fn(),
}));

vi.mock("../lib/api", () => ({
  ApiError: class extends Error {},
  judge: { get: () => "key", requestUnlock: () => undefined },
  runSettings: {
    get: () => Promise.resolve({ settings: rows }),
    save: (changes: Record<string, number>) => {
      saved.push(changes);
      return Promise.resolve({
        settings: rows.map((r) =>
          r.key in changes ? { ...r, value: changes[r.key] } : r,
        ),
      });
    },
    reset: () => {
      reset();
      return Promise.resolve({ settings: rows });
    },
  },
}));

describe("Settings", () => {
  it("switches the theme from General", async () => {
    const onTheme = vi.fn();
    render(
      <Settings onClose={() => undefined} theme="auto" onTheme={onTheme} />,
    );
    expect(screen.getByRole("radio", { name: "System" })).toBeChecked();
    await userEvent.click(screen.getByRole("radio", { name: "Dark" }));
    expect(onTheme).toHaveBeenCalledWith("dark");
  });

  it("saves only what changed, refuses a value out of range, and resets", async () => {
    render(
      <Settings
        onClose={() => undefined}
        theme="auto"
        onTheme={() => undefined}
      />,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Runs and plans" }),
    );
    const calls = await screen.findByRole("spinbutton", {
      name: "Tool calls per run",
    });
    expect(screen.getByText("5–60")).toBeInTheDocument(); // the range, under the box
    expect(
      screen.queryByRole("button", { name: /back to the default/ }),
    ).toBeNull(); // at its default
    const save = screen.getByRole("button", { name: "Save" });
    expect(save).toBeDisabled();
    await userEvent.clear(calls);
    await userEvent.type(calls, "99");
    expect(save).toBeDisabled(); // out of range
    await userEvent.clear(calls);
    await userEvent.type(calls, "30");
    expect(
      screen.getByRole("button", {
        name: "Tool calls per run: back to the default, 25",
      }),
    ).toBeInTheDocument();
    await userEvent.click(save);
    await waitFor(() => expect(saved).toEqual([{ run_tool_calls: 30 }]));
    expect(await screen.findByText("Saved.")).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Reset to defaults" }),
    );
    await waitFor(() => expect(reset).toHaveBeenCalled());
    expect(
      screen.getByRole("spinbutton", { name: "Tool calls per run" }),
    ).toHaveValue(25);
  });
});
