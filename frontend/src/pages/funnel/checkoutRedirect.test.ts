import { describe, expect, it } from "vitest";
import { fakeCheckoutPath, isStripeCheckoutUrl } from "./checkoutRedirect";

describe("fakeCheckoutPath", () => {
  const origin = window.location.origin;

  it("accepts the relative fake checkout path and the same-origin absolute URL", () => {
    expect(fakeCheckoutPath("/fake-checkout/cs_fake_abc-123")).toBe("/fake-checkout/cs_fake_abc-123");
    expect(fakeCheckoutPath(`${origin}/fake-checkout/cs_fake_abc`)).toBe("/fake-checkout/cs_fake_abc");
  });

  it.each([
    "https://evil.example.com/fake-checkout/cs_fake_abc",
    "//evil.example.com/fake-checkout/cs_fake_abc",
    "/\\evil.example.com/fake-checkout/x",
    "javascript:alert(1)",
    "/paywall",
    "/fake-checkout/",
    "/fake-checkout/a/b",
    "/fake-checkout/a?next=https://evil.example.com",
    "/fake-checkout/a#x",
    `${origin}.evil.example.com/fake-checkout/a`,
    "https://checkout.stripe.com/c/pay/x",
    "",
  ])("refuses %s", (url) => {
    expect(fakeCheckoutPath(url)).toBeNull();
  });

  it("does not loosen the Stripe check", () => {
    expect(isStripeCheckoutUrl("/fake-checkout/cs_fake_abc")).toBe(false);
    expect(isStripeCheckoutUrl("https://evil.example.com/pay")).toBe(false);
  });
});
