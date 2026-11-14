import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { crisisStore } from "../../api/useCrisisResources";
import { pricingStore } from "../../api/usePricing";
import type { CrisisResourcesResponse, PricingResponse } from "../../api/types";
import PricingPage from "./PricingPage";

const pricing: PricingResponse = {
  currency: "USD",
  defaultPlanId: "four_week",
  plans: [
    {
      id: "four_week", label: "4 weeks", priceToday: 14.99, renewalPrice: 29.99,
      introPeriodText: "4 weeks", renewPeriodText: "4 weeks", introDays: 28, renewDays: 28, firstRenewalDate: null,
    },
    {
      id: "twelve_week", label: "12 weeks", priceToday: 49.99, renewalPrice: 69.99,
      introPeriodText: "12 weeks", renewPeriodText: "12 weeks", introDays: 84, renewDays: 84, firstRenewalDate: null,
    },
  ],
};
const crisis: CrisisResourcesResponse = {
  verifyBeforeLaunch: true,
  resources: [
    { id: "a", name: "Emergency services", phone: "911", description: "" },
    { id: "b", name: "988 Suicide & Crisis Lifeline", phone: "988", description: "" },
    { id: "c", name: "Alzheimer's Association 24/7 Helpline", phone: "1-800-272-3900", description: "" },
    { id: "d", name: "Eldercare Locator", phone: "1-800-677-1116", description: "" },
  ],
};

const json = (b: unknown, status = 200) =>
  new Response(JSON.stringify(b), { status, headers: { "Content-Type": "application/json" } });
const fetchMock = vi.fn<typeof fetch>();

function mockApi(opts: { pricingFails?: boolean; crisisFails?: boolean } = {}) {
  fetchMock.mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/pricing")) return Promise.resolve(opts.pricingFails ? json({}, 500) : json(pricing));
    return Promise.resolve(opts.crisisFails ? json({}, 500) : json(crisis));
  });
}
const renderPage = () =>
  render(
    <MemoryRouter>
      <PricingPage />
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  pricingStore.reset();
  crisisStore.reset();
});
afterEach(() => vi.unstubAllGlobals());

describe("PricingPage", () => {
  it("shows API prices in API order with the template wording", async () => {
    mockApi();
    renderPage();
    expect(await screen.findByText("$14.99")).toBeInTheDocument();
    const names = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(names.indexOf("4 weeks")).toBeLessThan(names.indexOf("12 weeks"));
    expect(screen.getByText("$49.99")).toBeInTheDocument();
    expect(screen.getByText("Then $29.99 every 4 weeks")).toBeInTheDocument();
    expect(screen.getByText("Then $69.99 every 12 weeks")).toBeInTheDocument();
    expect(screen.getByText("for your first 12 weeks")).toBeInTheDocument();
    expect(screen.getByText("Prices in USD")).toBeInTheDocument();
    for (const link of screen.getAllByRole("link", { name: /Mom/ })) {
      expect(link).toHaveAttribute("href", "/quiz");
    }
  });

  it("follows the order the API returns", async () => {
    mockApi();
    fetchMock.mockImplementation((input) =>
      Promise.resolve(
        String(input).endsWith("/pricing")
          ? json({ ...pricing, plans: [...pricing.plans].reverse() })
          : json(crisis),
      ),
    );
    renderPage();
    await screen.findByText("$14.99");
    const text = document.body.textContent ?? "";
    expect(text.indexOf("$49.99")).toBeLessThan(text.indexOf("$14.99"));
  });

  it("shows an error with retry and no amounts when pricing fails", async () => {
    mockApi({ pricingFails: true });
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent("We could not load the prices.");
    expect(document.body.textContent).not.toMatch(/\$\d/);
    mockApi();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("$14.99")).toBeInTheDocument();
  });

  it("renders crisis numbers from the API as tel links, including a fourth", async () => {
    mockApi();
    renderPage();
    const section = screen.getByRole("region", { name: "Need help now?" });
    await waitFor(() => expect(within(section).getAllByRole("link")).toHaveLength(4));
    const hrefs = within(section).getAllByRole("link").map((a) => a.getAttribute("href"));
    expect(hrefs).toEqual(["tel:911", "tel:988", "tel:18002723900", "tel:18006771116"]);
    expect(section).toHaveTextContent("Adult Protective Services in your state");
  });

  it("falls back to bundled crisis numbers when the request fails", async () => {
    mockApi({ crisisFails: true, pricingFails: true });
    renderPage();
    const section = screen.getByRole("region", { name: "Need help now?" });
    await screen.findByRole("alert");
    const hrefs = within(section).getAllByRole("link").map((a) => a.getAttribute("href"));
    expect(hrefs).toEqual(["tel:911", "tel:988", "tel:18002723900"]);
  });

  it("has no discount, per-day or false-privacy wording", async () => {
    mockApi();
    renderPage();
    await screen.findByText("$14.99");
    const text = document.body.textContent ?? "";
    for (const bad of [/\/day/i, /per day/i, /\bsave\b/i, /% off/i, /limited time/i, /most popular/i, /stay in your browser/i, /in your browser/i]) {
      expect(text).not.toMatch(bad);
    }
    expect(screen.getByText("Saved privately to this session")).toBeInTheDocument();
    expect(screen.getByText("No ad tracking")).toBeInTheDocument();
    expect(screen.getByText("Practice isn’t recorded")).toBeInTheDocument();
  });

  it("has one h1, three FAQ items, and is axe clean", async () => {
    mockApi();
    const { container } = renderPage();
    await screen.findByText("$14.99");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(container.querySelectorAll("details")).toHaveLength(3);
    expect(await axe(container)).toHaveNoViolations();
  });
});
