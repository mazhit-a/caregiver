import { useCallback, useEffect, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router";
import { AppDataProvider, useAppCopy } from "../../api/AppDataProvider";
import {
  type AppFailure,
  type ApiFailure,
  gateRoute,
  isShellFailure,
} from "../../api/errors";
import { clearToken } from "../../api/session";
import { StatusBlock } from "../../components/StatusBlock";
import { HelpSheet } from "../HelpSheet";
import { NOT_MEDICAL_ADVICE } from "../nav";
import { SkipLink } from "../SkipLink";
import { ROUTES } from "../../routes";
import type { AppContext } from "./appContext";
import { AppSidebar } from "./AppSidebar";
import { AppTabBar } from "./AppTabBar";
import { AppTopBar } from "./AppTopBar";
import { PastDueNotice } from "./PastDueNotice";
import { readNavCopy } from "./navCopy";
import { isFullScreenRoute } from "./tabs";
import { useIsDesktop } from "./useIsDesktop";
import { useRouteFocus } from "./useRouteFocus";
import styles from "./AppLayout.module.css";

type Outcome =
  | { kind: "none" }
  | { kind: "redirect"; to: string; restore: boolean }
  | { kind: "past_due"; message?: string };

function outcomeFor(failure: AppFailure, message?: string): Outcome | null {
  if (!isShellFailure(failure)) return null;
  if (failure.kind === "session_lost") {
    clearToken();
    return { kind: "redirect", to: ROUTES.quiz, restore: true };
  }
  if (failure.kind === "gate") {
    const target = gateRoute(failure.reason);
    if (target.notice === "past_due") return { kind: "past_due", message };
    return { kind: "redirect", to: target.path, restore: false };
  }
  return null;
}

/** Shell for every signed-in app route: sidebar from 1024px, top bar and tab bar below. */
export function AppLayout() {
  return (
    <AppDataProvider>
      <AppShell />
    </AppDataProvider>
  );
}

function AppShell() {
  const { pathname } = useLocation();
  const desktop = useIsDesktop();
  const fullScreen = isFullScreenRoute(pathname);
  const [helpOpen, setHelpOpen] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>({ kind: "none" });
  const appCopy = useAppCopy();
  const nav = appCopy.status === "ready" ? readNavCopy(appCopy.data.nav) : null;
  useRouteFocus();

  useEffect(() => {
    const root = document.documentElement;
    const name = styles["rootPadding"] ?? "";
    if (name) root.classList.add(name);
    return () => {
      if (name) root.classList.remove(name);
    };
  }, []);

  const reportFailure = useCallback(
    (failure: ApiFailure, message?: string): boolean => {
      const next = outcomeFor(failure, message);
      if (next) setOutcome(next);
      return next !== null;
    },
    [],
  );

  const loadOutcome =
    appCopy.status === "error" ? outcomeFor(appCopy.error) : null;
  const active = loadOutcome ?? outcome;
  if (active.kind === "redirect") {
    return (
      <Navigate
        to={active.to}
        replace
        state={active.restore ? { restore: true } : null}
      />
    );
  }

  const context: AppContext = {
    openHelp: () => setHelpOpen(true),
    reportFailure,
  };
  const labels = nav;
  const showTabBar = !desktop && !fullScreen && labels !== null;

  return (
    <div
      className={styles.shell}
      data-fullscreen={fullScreen ? "true" : undefined}
    >
      <SkipLink />
      {desktop ? (
        <AppSidebar copy={labels} onHelp={context.openHelp} />
      ) : (
        <AppTopBar
          copy={labels}
          onHelp={context.openHelp}
          compact={fullScreen}
        />
      )}
      <main id="main" tabIndex={-1} className={styles.main}>
        <div className={styles.column}>
          {active.kind === "past_due" && labels && (
            <PastDueNotice
              message={active.message}
              settingsLabel={labels.settings}
            />
          )}
          {labels ? (
            <Outlet context={context} />
          ) : (
            <StatusBlock
              status={appCopy.status === "loading" ? "loading" : "error"}
              what="your page"
              onRetry={appCopy.refresh}
            />
          )}
          {!desktop && !fullScreen && (
            <p className={styles.disclaimer}>{NOT_MEDICAL_ADVICE}</p>
          )}
        </div>
      </main>
      {showTabBar && labels && <AppTabBar copy={labels} />}
      <HelpSheet open={helpOpen} onClose={() => setHelpOpen(false)} />
    </div>
  );
}
