import { createContext, useContext } from "react";

/** Lets a Today section ask the page to refetch `GET /api/today` (the page provides it). */
export const TodayRefreshContext = createContext<() => void>(() => undefined);
export const useTodayRefresh = (): (() => void) => useContext(TodayRefreshContext);
