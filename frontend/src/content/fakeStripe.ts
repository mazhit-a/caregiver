/**
 * Stripe's documented test cards (https://docs.stripe.com/testing/overview) as the in-app
 * simulated checkout understands them. Typed constant: the backend does not expose the list.
 * Any future expiry and any 3-4 digit CVC are accepted; unknown numbers are declined.
 */
export interface TestCard {
  number: string;
  outcome: string;
}

export const TEST_CARDS: readonly TestCard[] = [
  { number: "4242 4242 4242 4242", outcome: "Payment succeeds" },
  { number: "4000 0000 0000 0002", outcome: "Declined (card_declined)" },
  { number: "4000 0000 0000 9995", outcome: "Declined (insufficient_funds)" },
  { number: "4000 0000 0000 0069", outcome: "Declined (expired_card)" },
  { number: "4000 0000 0000 0127", outcome: "Declined (incorrect_cvc)" },
  { number: "4000 0000 0000 0341", outcome: "Succeeds, but the first renewal payment fails" },
  { number: "4000 0025 0000 3155", outcome: "Needs 3-D Secure authentication" },
] as const;

export const FAKE_CHECKOUT_TEXT = {
  banner: "Simulated checkout. No real payment.",
  title: "Pay with a test card",
  loading: "Loading your checkout",
  notFound: "We couldn't find that checkout. Go back to the paywall and start again.",
  loadFailed: "We couldn't load the checkout. Please try again.",
  retry: "Try again",
  toPaywall: "Back to the paywall",
  numberLabel: "Card number",
  expiryLabel: "Expiry (MM/YY)",
  cvcLabel: "CVC",
  pay: "Pay",
  paying: "Paying...",
  authenticate: "Authenticate",
  authenticateHint: "This test card asks for 3-D Secure. Authenticate to finish the simulated payment.",
  testCards: "Test cards",
  useCard: "Use",
  testCardsHint: "Any future expiry and any 3 or 4 digit CVC work. Unknown numbers are declined.",
  badExpiry: "Enter the expiry as MM/YY, for example 12/34.",
  badNumber: "Enter the card number.",
  badCvc: "Enter the 3 or 4 digit CVC.",
  genericError: "The simulated payment didn't go through. Please try again.",
  closed: "This checkout is already closed. Go back to the paywall.",
} as const;
