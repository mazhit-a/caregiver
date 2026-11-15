import { demoJumpToRenewal, demoNextDay } from "../../../api/app";
import type { Demo } from "../../../api/appTypes";

/**
 * Control id (from Today's `demo.controls`) to the endpoint it calls. The one table; an id that is
 * not here is not rendered. `fail-next-payment` lives only on the Settings panel.
 */
export const DEMO_ACTIONS: Record<string, (signal?: AbortSignal) => Promise<Demo>> = {
  nextDay: demoNextDay,
  jumpToRenewal: demoJumpToRenewal,
};
