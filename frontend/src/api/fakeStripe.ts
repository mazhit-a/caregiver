import { apiGet, apiRequest } from "./client";

/** Simulated checkout (backend `FAKE_STRIPE=true`). Public: the secret checkout id is the capability. */
export interface FakeCheckoutSummary {
  fake: true;
  checkoutId: string;
  status: "open" | "paid" | "canceled";
  planId: string;
  planLabel: string;
  currency: string;
  amountToday: number;
  introPeriodText: string;
  renewalPrice: number;
  renewPeriodText: string;
  firstRenewalDate: string;
  displayLabel: string | null;
  successUrl: string;
  cancelUrl: string;
}

export interface FakeCardInput {
  cardNumber: string;
  expMonth: number;
  expYear: number;
  cvc: string;
  authenticated?: boolean;
}

export interface FakePayResult {
  fake: true;
  status: "paid" | "requires_action";
  successUrl: string;
}

export interface FakeCancelResult {
  fake: true;
  status: "canceled";
  cancelUrl: string;
}

const base = (id: string): string => `/fake-stripe/checkout/${encodeURIComponent(id)}`;

export function getFakeCheckout(id: string, signal?: AbortSignal): Promise<FakeCheckoutSummary> {
  return apiGet<FakeCheckoutSummary>(base(id), signal);
}

export function payFakeCheckout(id: string, body: FakeCardInput, signal?: AbortSignal): Promise<FakePayResult> {
  return apiRequest<FakePayResult>({ method: "POST", path: `${base(id)}/pay`, body, signal, auth: false });
}

export function cancelFakeCheckout(id: string, signal?: AbortSignal): Promise<FakeCancelResult> {
  return apiRequest<FakeCancelResult>({ method: "POST", path: `${base(id)}/cancel`, signal, auth: false });
}
