/* An action that needs the judge password: with none kept, the dialog opens and the action does
   not run (the reader sends it again once unlocked); a password the server calls wrong is
   dropped and the dialog opens the same way; no error either time. */

import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  key: "",
  answers: [] as boolean[],
  asked: 0,
}));
vi.mock("./api", async (importOriginal) => {
  const real = await importOriginal<typeof import("./api")>();
  return {
    ...real,
    judge: {
      get: () => state.key,
      set: (v: string) => {
        state.key = v;
      },
      requestUnlock: () => {
        state.asked += 1;
        const yes = state.answers.shift() ?? false;
        if (yes) state.key = "right";
        return Promise.resolve(yes);
      },
    },
  };
});

import { ApiError } from "./api";
import { withJudge } from "./withJudge";

describe("withJudge", () => {
  beforeEach(() => {
    state.key = "";
    state.answers = [];
    state.asked = 0;
  });

  it("opens the dialog and does not run the action when the tab has no password", async () => {
    state.answers = [true];
    const work = vi.fn(() => Promise.resolve("started"));
    expect(await withJudge(work)).toBeNull();
    expect(state.asked).toBe(1);
    expect(work).not.toHaveBeenCalled(); // unlocking does not send it: the reader does
  });

  it("runs the action when the tab has the password", async () => {
    state.key = "right";
    expect(await withJudge(() => Promise.resolve("started"))).toBe("started");
    expect(state.asked).toBe(0);
  });

  it("drops a wrong password and opens the dialog, without trying again", async () => {
    state.key = "old";
    const work = vi.fn().mockRejectedValueOnce(new ApiError(401, "wrong"));
    expect(await withJudge(work)).toBeNull();
    expect(state.key).toBe("");
    expect(state.asked).toBe(1);
    expect(work).toHaveBeenCalledTimes(1);
  });

  it("passes any other error to the caller", async () => {
    state.key = "right";
    await expect(
      withJudge(() => Promise.reject(new ApiError(409, "still going"))),
    ).rejects.toThrow("still going");
    expect(state.asked).toBe(0);
  });
});
