import { useCrisisResources } from "../api/useCrisisResources";
import { CRISIS_FALLBACK } from "../api/crisisFallback";
import type { CrisisResource } from "../api/types";

/** API resources, or the bundled numbers while loading or on failure: help is never blank. */
export function useCrisisList(): readonly CrisisResource[] {
  const { data } = useCrisisResources();
  return data?.resources ?? CRISIS_FALLBACK;
}
