const STRIPE_HOST = "checkout.stripe.com";

/** True only for an https URL on the Stripe Checkout host. Anything else must not be followed. */
export function isStripeCheckoutUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" && parsed.hostname === STRIPE_HOST && parsed.username === "";
  } catch {
    return false;
  }
}

/** Leaves the app for Stripe. Kept in its own module so tests can replace the page jump. */
export function goToCheckout(url: string): void {
  window.location.assign(url);
}

const FAKE_PATH = /^\/fake-checkout\/([A-Za-z0-9_-]{1,128})$/;

/**
 * The in-app path of a simulated checkout, or null. Accepts only the relative path
 * `/fake-checkout/<id>` or the same path on this page's own origin; nothing else is followed.
 */
export function fakeCheckoutPath(url: string): string | null {
  const origin = window.location.origin;
  const relative = url.startsWith("/") && !url.startsWith("//") && !url.includes("\\");
  if (!relative && !url.startsWith(`${origin}/`)) return null;
  const path = relative ? url : url.slice(origin.length);
  return FAKE_PATH.test(path) ? path : null;
}
