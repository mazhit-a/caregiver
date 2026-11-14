import { useEffect } from "react";
import { useLocation } from "react-router";

/**
 * On step change: scroll to the top and move focus to the step heading
 * (`[data-funnel-heading]`, falling back to `<main>`). The first screen of a visit is skipped,
 * so the skip link stays the first tab stop.
 */
export function useStepFocus(shouldFocus: () => boolean): void {
  const { pathname } = useLocation();
  useEffect(() => {
    if (!shouldFocus()) return;
    window.scrollTo(0, 0);
    const target =
      document.querySelector<HTMLElement>("[data-funnel-heading]") ??
      document.getElementById("main");
    target?.focus({ preventScroll: true });
    // shouldFocus is stable for the layout's lifetime.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);
}
