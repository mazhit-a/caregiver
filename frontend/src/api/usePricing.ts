import { createResourceStore, useResource, type Resource } from "./useResource";
import type { PricingResponse } from "./types";

export const pricingStore = createResourceStore<PricingResponse>("/pricing");

export function usePricing(): Resource<PricingResponse> {
  return useResource(pricingStore);
}
