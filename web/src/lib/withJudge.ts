import { ApiError, judge } from "./api";

/* Run an action that needs the judge password. With none kept, the dialog opens and the action
   does not run: what the reader wrote stays where it is, and they send it again once unlocked.
   If the server says the kept password is wrong, it is dropped and the dialog opens the same
   way. No error is shown for either: the dialog is the answer. Resolves to the action's result,
   or null when it did not run. Any other error is thrown to the caller as before. */
export async function withJudge<T>(work: () => Promise<T>): Promise<T | null> {
  if (!judge.get()) {
    void judge.requestUnlock();
    return null;
  }
  try {
    return await work();
  } catch (e) {
    if (!(e instanceof ApiError && e.status === 401)) throw e;
    judge.set("");
    void judge.requestUnlock();
    return null;
  }
}
