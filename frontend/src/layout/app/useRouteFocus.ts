import { useEffect, useRef } from "react";
import { useLocation } from "react-router";

const findTarget = (): HTMLElement | null =>
  document.querySelector<HTMLElement>("[data-app-heading]") ??
  document.getElementById("main");

/**
 * On every route change after the first screen of a visit: scroll to the top and focus the page
 * `h1` (`[data-app-heading]`, falling back to `<main>`). When a page swaps its loading heading for
 * the real one and the focused node disappears, focus follows to the new heading.
 */
export function useRouteFocus(): void {
  const { pathname } = useLocation();
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    window.scrollTo(0, 0);
    let focused = findTarget();
    focused?.focus({ preventScroll: true });
    const main = document.getElementById("main");
    if (!main) return;
    const observer = new MutationObserver(() => {
      if (
        !focused ||
        focused.isConnected ||
        document.activeElement !== document.body
      )
        return;
      focused = findTarget();
      focused?.focus({ preventScroll: true });
    });
    observer.observe(main, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [pathname]);
}
