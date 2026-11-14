// Hand-written to match backend/app/presentation/api (camelCase).

export interface PricingPlan {
  id: string;
  label: string;
  priceToday: number;
  renewalPrice: number;
  introPeriodText: string;
  renewPeriodText: string;
  introDays: number;
  renewDays: number;
  /** Null when the request has no session. */
  firstRenewalDate: string | null;
}

export interface PricingResponse {
  currency: string;
  defaultPlanId: string;
  plans: PricingPlan[];
}

export interface CrisisResource {
  id: string;
  name: string;
  phone: string;
  description: string;
}

export interface CrisisResourcesResponse {
  resources: CrisisResource[];
  verifyBeforeLaunch: boolean;
}
