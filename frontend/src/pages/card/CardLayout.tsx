import { Outlet } from "react-router";

/** Bare layout for the public care card: no nav, no session logic. G17 owns and replaces this file. */
export function CardLayout() {
  return <Outlet />;
}
