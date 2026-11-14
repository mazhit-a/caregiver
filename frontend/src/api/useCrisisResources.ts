import { createResourceStore, useResource, type Resource } from "./useResource";
import type { CrisisResourcesResponse } from "./types";

export const crisisStore = createResourceStore<CrisisResourcesResponse>("/resources/crisis");

export function useCrisisResources(): Resource<CrisisResourcesResponse> {
  return useResource(crisisStore);
}
