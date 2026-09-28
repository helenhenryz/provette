/* The gate before the planner, as the Write composer shows it: a message with no lab word comes
   back refused with its sentence and a "Send anyway" that sends it past the gate. */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { HomePage } from "./Home";

const { startPlan } = vi.hoisted(() => ({ startPlan: vi.fn() }));

vi.mock("../lib/api", () => {
  class ApiError extends Error {
    status: number;
    code: string | null;
    constructor(status: number, message: string, code: string | null = null) {
      super(message);
      this.status = status;
      this.code = code;
    }
  }
  startPlan.mockImplementation(
    (_request: string, _technique: string | null, anyway: boolean) =>
      anyway
        ? Promise.resolve({ id: "plan9" })
        : Promise.reject(
            new ApiError(
              422,
              "This does not read as a liquid-handling request.",
              "not_a_request",
            ),
          ),
  );
  return {
    ApiError,
    judge: { get: () => "key", requestUnlock: () => undefined },
    api: {
      episodes: () =>
        Promise.resolve({
          episodes: [],
          sets: [],
          current_sets: [],
          prices_read_on: null,
        }),
    },
    live: {
      status: () =>
        Promise.resolve({
          enabled: true,
          model: "m",
          model_label: "Nemotron 3 Test 1B",
          runner: "r",
          runner_label: "R",
          cap_usd: 1,
          spent_today_usd: 0,
          remaining_usd: 1,
          running: 0,
          examples: [],
        }),
      runs: () => Promise.resolve({ runs: [] }),
      plans: () => Promise.resolve({ plans: [] }),
      startPlan,
    },
  };
});

describe("HomePage, the gate", () => {
  it("shows the refusal with Send anyway, which sends past the gate", async () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    await screen.findByText("Nemotron 3 Test 1B");
    await userEvent.type(
      screen.getByRole("textbox"),
      "What is the purpose of life?",
    );
    await userEvent.click(screen.getByRole("button", { name: "Write it" }));
    expect(await screen.findByText("Not a lab request")).toBeInTheDocument();
    expect(startPlan).toHaveBeenLastCalledWith(
      "What is the purpose of life?",
      null,
      false,
    );
    await userEvent.click(screen.getByRole("button", { name: "Send anyway" }));
    expect(startPlan).toHaveBeenLastCalledWith(
      "What is the purpose of life?",
      null,
      true,
    );
  });
});
