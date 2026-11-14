import { useEffect } from "react";
import { useLocation } from "react-router";

const findTarget = (): HTMLElement | null =>
  document.querySelector<HTMLElement>("[data-funnel-heading]") ?? document.getElementById("main");

/**
 * On step change: scroll to the top and move focus to the step heading
 * (`[data-funnel-heading]`, falling back to `<main>`). The first screen of a visit is skipped,
 * so the skip link stays the first tab stop.
 *
 * Pages that load data show a heading first ("Getting your plan") and swap in the real one when
 * the data arrives. When that swap removes the focused heading, focus follows to the new heading
 * instead of dropping to `<body>` (which would restart keyboard users at the skip link).
 */
export function useStepFocus(shouldFocus: () => boolean): void {
  const { pathname } = useLocation();
  useEffect(() => {
    if (!shouldFocus()) return;
    window.scrollTo(0, 0);
    let focused = findTarget();
    focused?.focus({ preventScroll: true });

    const main = document.getElementById("main");
    if (!main) return;
    const observer = new MutationObserver(() => {
      if (!focused || focused.isConnected || document.activeElement !== document.body) return;
      focused = findTarget();
      focused?.focus({ preventScroll: true });
    });
    observer.observe(main, { childList: true, subtree: true });
    return () => observer.disconnect();
    // shouldFocus is stable for the layout's lifetime.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);
}
