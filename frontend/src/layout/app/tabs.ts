import { matchPath } from "react-router";
import { ROUTES } from "../../routes";
import type { NavCopy } from "./navCopy";

export interface AppTab {
  key: "today" | "plan" | "profilePage" | "skills";
  to: string;
  /** Routes that highlight this tab (the lesson player and visit sheet keep Today lit). */
  matches: readonly string[];
}

export const APP_TABS: readonly AppTab[] = [
  {
    key: "today",
    to: ROUTES.today,
    matches: ["/today/*", ROUTES.lesson, ROUTES.visitSheet],
  },
  { key: "plan", to: ROUTES.appPlan, matches: [ROUTES.appPlan] },
  {
    key: "profilePage",
    to: ROUTES.profile,
    matches: [ROUTES.profile, ROUTES.careCard],
  },
  { key: "skills", to: ROUTES.skills, matches: [ROUTES.skills] },
];

export const isTabActive = (tab: AppTab, pathname: string): boolean =>
  tab.matches.some((pattern) => matchPath(pattern, pathname) !== null) ||
  (tab.key === "today" && pathname === ROUTES.today);

export const isSettingsActive = (pathname: string): boolean =>
  matchPath("/settings/*", pathname) !== null;

/** Lesson player and practice round: full-screen on mobile (no tab bar). */
export const isFullScreenRoute = (pathname: string): boolean =>
  matchPath(ROUTES.lesson, pathname) !== null ||
  pathname === ROUTES.todayPractice;

export const tabLabel = (copy: NavCopy, key: AppTab["key"]): string =>
  copy[key];
