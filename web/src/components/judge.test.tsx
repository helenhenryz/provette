/* The judge password dialog: a wrong password is said at once and not kept, the right one is
   kept and closes the dialog, Escape closes it, and an unlocked tab can lock again. */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { judge } from "../lib/api";
import { JudgeDialog } from "./JudgeDialog";

const RIGHT = "amber-pipette-harbor-42";

function serve() {
  vi.stubGlobal(
    "fetch",
    vi.fn((_url: string, init: RequestInit) => {
      const given = (init.headers as Record<string, string>)[
        "X-Judge-Password"
      ];
      return Promise.resolve(
        new Response(null, { status: given === RIGHT ? 204 : 401 }),
      );
    }),
  );
}

describe("JudgeDialog", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    sessionStorage.clear();
  });

  it("says a wrong password at once, keeps the right one, and closes", async () => {
    serve();
    const onClose = vi.fn();
    const onChange = vi.fn();
    render(<JudgeDialog open onClose={onClose} onChange={onChange} />);
    const dialog = screen.getByRole("dialog", {
      name: "Enter the judge password",
    });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    const field = screen.getByLabelText("Judge password");
    expect(screen.getByRole("button", { name: "Unlock" })).toBeDisabled();

    await userEvent.type(field, "amber");
    await userEvent.click(screen.getByRole("button", { name: "Unlock" }));
    expect(
      await screen.findByText("That password isn't right."),
    ).toBeInTheDocument();
    expect(judge.get()).toBe("");
    expect(onClose).not.toHaveBeenCalled();

    await userEvent.clear(field);
    await userEvent.type(field, `${RIGHT}{Enter}`);
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(judge.get()).toBe(RIGHT);
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("shows the password on asking, closes on Escape, and an unlocked tab can lock", async () => {
    const onClose = vi.fn();
    const onChange = vi.fn();
    const { unmount } = render(
      <JudgeDialog open onClose={onClose} onChange={onChange} />,
    );
    const field = screen.getByLabelText("Judge password");
    expect(field).toHaveAttribute("type", "password");
    await userEvent.click(
      screen.getByRole("button", { name: "Show the password" }),
    );
    expect(field).toHaveAttribute("type", "text");
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
    unmount();

    judge.set(RIGHT);
    render(<JudgeDialog open onClose={onClose} onChange={onChange} />);
    expect(
      screen.getByRole("dialog", { name: "Unlocked" }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Lock" }));
    expect(judge.get()).toBe("");
    expect(onChange).toHaveBeenCalledWith(false);
  });
});
