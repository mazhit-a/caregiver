import { useEffect, useSyncExternalStore } from "react";
import { apiGet } from "./client";

export type ResourceState<T> =
  | { status: "loading"; data: undefined }
  | { status: "error"; data: undefined }
  | { status: "ready"; data: T };

export type Resource<T> = ResourceState<T> & { retry: () => void };

export interface ResourceStore<T> {
  subscribe: (listener: () => void) => () => void;
  getSnapshot: () => ResourceState<T>;
  /** Starts the request once per page load. */
  ensureLoaded: () => void;
  /** Starts a new request unless one is in flight. */
  retry: () => void;
  /** Test helper: forget the cached result. */
  reset: () => void;
}

/** One module-level store per path: all consumers share one request per page load. */
export function createResourceStore<T>(path: string): ResourceStore<T> {
  const loading: ResourceState<T> = { status: "loading", data: undefined };
  let state: ResourceState<T> = loading;
  let inFlight = false;
  let started = false;
  const listeners = new Set<() => void>();

  const set = (next: ResourceState<T>): void => {
    state = next;
    listeners.forEach((l) => l());
  };

  const retry = (): void => {
    if (inFlight) return;
    inFlight = true;
    started = true;
    if (state.status !== "loading") set(loading);
    apiGet<T>(path)
      .then((data) => set({ status: "ready", data }))
      .catch(() => set({ status: "error", data: undefined }))
      .finally(() => {
        inFlight = false;
      });
  };

  return {
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    getSnapshot: () => state,
    ensureLoaded() {
      if (!started) retry();
    },
    retry,
    reset() {
      state = loading;
      inFlight = false;
      started = false;
    },
  };
}

export function useResource<T>(store: ResourceStore<T>): Resource<T> {
  const state = useSyncExternalStore(store.subscribe, store.getSnapshot);
  useEffect(() => {
    store.ensureLoaded();
  }, [store]);
  return { ...state, retry: store.retry } as Resource<T>;
}
