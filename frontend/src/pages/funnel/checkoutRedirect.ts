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
