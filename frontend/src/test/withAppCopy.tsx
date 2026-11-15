import type { ReactNode } from "react";
import { AppDataProvider } from "../api/AppDataProvider";

/** Mounts the shell's copy provider around a page under test (the real shell does this in `AppLayout`). */
export function WithAppCopy({ children }: { children: ReactNode }) {
  return <AppDataProvider>{children}</AppDataProvider>;
}
