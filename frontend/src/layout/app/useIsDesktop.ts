import { useSyncExternalStore } from "react";

/**
 * 1024px: the prototype's sidebar layout wraps at about 824px (264 + 560); 1024 keeps iPad portrait
 * (768 to 1023) on the top bar and tab bar. The CSS modules use the same literal.
 */
export const DESKTOP_QUERY = "(min-width: 1024px)";

const list = (): MediaQueryList | null =>
  typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia(DESKTOP_QUERY)
    : null;

function subscribe(onChange: () => void): () => void {
  const mq = list();
  mq?.addEventListener("change", onChange);
  return () => mq?.removeEventListener("change", onChange);
}

/** True at 1024px and up (sidebar); false without matchMedia (tab bar). */
export function useIsDesktop(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => list()?.matches ?? false,
    () => false,
  );
}
