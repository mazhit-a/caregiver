import { useEffect, useRef, useState } from "react";
import { Outlet, useOutletContext } from "react-router";
import { HelpSheet } from "../HelpSheet";
import { SkipLink } from "../SkipLink";
import styles from "./FunnelLayout.module.css";

export interface FunnelContext {
  openHelp: () => void;
  /** False for the first screen of a visit, true afterwards (used by useStepFocus). */
  shouldFocusStep: () => boolean;
}

export function useFunnelContext(): FunnelContext {
  return useOutletContext<FunnelContext>();
}

/** Focused shell for the quiz, plan, paywall and checkout: no site nav. */
export function FunnelLayout() {
  const [helpOpen, setHelpOpen] = useState(false);
  const seenFirst = useRef(false);
  useEffect(() => {
    const root = document.documentElement;
    const name = styles["rootPadding"] ?? "";
    if (name) root.classList.add(name);
    return () => {
      if (name) root.classList.remove(name);
    };
  }, []);
  const context: FunnelContext = {
    openHelp: () => setHelpOpen(true),
    shouldFocusStep: () => {
      const focus = seenFirst.current;
      seenFirst.current = true;
      return focus;
    },
  };
  return (
    <div className={styles.shell}>
      <SkipLink />
      <Outlet context={context} />
      <HelpSheet open={helpOpen} onClose={() => setHelpOpen(false)} />
    </div>
  );
}
