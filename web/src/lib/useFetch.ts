import { useEffect, useState } from "react";
import { ApiError } from "./api";

export interface Fetched<T> {
  data: T | null;
  error: string | null;
  status: number | null;
  loading: boolean;
}

/* Fetch once per `key`; the page renders loading, error or data. */
export function useFetch<T>(load: () => Promise<T>, key: string): Fetched<T> {
  const [state, setState] = useState<Fetched<T>>({
    data: null,
    error: null,
    status: null,
    loading: true,
  });
  useEffect(() => {
    let alive = true;
    setState({ data: null, error: null, status: null, loading: true });
    load().then(
      (data) =>
        alive && setState({ data, error: null, status: 200, loading: false }),
      (error: unknown) => {
        if (!alive) return;
        const status = error instanceof ApiError ? error.status : null;
        const message = error instanceof Error ? error.message : String(error);
        setState({ data: null, error: message, status, loading: false });
      },
    );
    return () => {
      alive = false;
    };
    // `load` is a fresh closure on every render; `key` is what says the fetch must run again.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return state;
}
