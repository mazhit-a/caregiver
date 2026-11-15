import { ROUTES } from "../routes";

export const MAIN_NAV = [
  { label: "How it works", to: ROUTES.how },
  { label: "Practice", to: ROUTES.practice },
  { label: "The course", to: ROUTES.course },
  { label: "Care tools", to: ROUTES.tools },
] as const;

export const FOOTER_NAV = [
  { label: "Home", to: ROUTES.home },
  { label: "The course", to: ROUTES.course },
  { label: "How it works", to: ROUTES.how },
  { label: "Care tools", to: ROUTES.tools },
  { label: "Practice", to: ROUTES.practice },
] as const;

export const NEED_HELP_NOW = "Need help now?"; // content/funnel-copy.json common.needHelpNow
