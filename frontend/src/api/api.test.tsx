import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, REQUEST_TIMEOUT_MS, apiGet } from "./client";
import { CRISIS_FALLBACK } from "./crisisFallback";
import { crisisStore, useCrisisResources } from "./useCrisisResources";
import { pricingStore, usePricing } from "./usePricing";
import { StatusBlock } from "../components/StatusBlock";
import type { CrisisResourcesResponse, PricingResponse } from "./types";

const json = (body: unknown, status = 200): Response =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  crisisStore.reset();
  pricingStore.reset();
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("apiGet", () => {
  it("returns parsed JSON from same-origin /api without a session header", async () => {
    fetchMock.mockResolvedValue(json({ ok: 1 }));
    await expect(apiGet("/pricing")).resolves.toEqual({ ok: 1 });
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/pricing");
    expect(JSON.stringify(init?.headers)).not.toMatch(/session/i);
  });

  it("parses the shared error shape on a 500", async () => {
    fetchMock.mockResolvedValue(
      json({ error: { code: "boom", message: "Broken.", details: { a: 1 } } }, 500),
    );
    const err = await apiGet("/x").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 500, code: "boom", message: "Broken.", details: { a: 1 } });
  });

  it("maps a non-shaped error body to http_error", async () => {
    fetchMock.mockResolvedValue(new Response("<html>", { status: 502 }));
    await expect(apiGet("/x")).rejects.toMatchObject({ status: 502, code: "http_error" });
  });

  it("maps a network failure to network_error", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(apiGet("/x")).rejects.toMatchObject({ code: "network_error" });
  });

  it("aborts after the timeout", async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(new DOMException("a", "AbortError")));
        }),
    );
    const promise = apiGet("/x").catch((e: unknown) => e);
    await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS);
    expect(await promise).toMatchObject({ code: "timeout" });
  });
});

const crisisBody: CrisisResourcesResponse = {
  verifyBeforeLaunch: true,
  resources: [{ id: "a", name: "A", phone: "911", description: "d" }],
};

function Consumer({ label }: { label: string }) {
  const crisis = useCrisisResources();
  if (crisis.status !== "ready") {
    return <StatusBlock status={crisis.status} what="help numbers" onRetry={crisis.retry} />;
  }
  return <p>{label}: {crisis.data.resources[0]?.phone}</p>;
}

describe("data hooks", () => {
  it("shares one request between two consumers", async () => {
    fetchMock.mockResolvedValue(json(crisisBody));
    render(
      <>
        <Consumer label="one" />
        <Consumer label="two" />
      </>,
    );
    expect(await screen.findByText("one: 911")).toBeInTheDocument();
    expect(screen.getByText("two: 911")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("shows loading, then an error with Try again, and retry recovers", async () => {
    let resolveFirst: (r: Response) => void = () => {};
    fetchMock
      .mockImplementationOnce(() => new Promise<Response>((r) => (resolveFirst = r)))
      .mockResolvedValueOnce(json(crisisBody));
    render(<Consumer label="one" />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
    await act(async () => resolveFirst(json({ error: { code: "x", message: "m", details: {} } }, 500)));
    await userEvent.click(await screen.findByRole("button", { name: "Try again" }));
    expect(await screen.findByText("one: 911")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("usePricing reads /api/pricing, including a null first renewal date", async () => {
    const body: PricingResponse = {
      currency: "USD",
      defaultPlanId: "four_week",
      plans: [
        {
          id: "four_week",
          label: "4 weeks",
          priceToday: 14.99,
          renewalPrice: 29.99,
          introPeriodText: "4 weeks",
          renewPeriodText: "4 weeks",
          introDays: 28,
          renewDays: 28,
          firstRenewalDate: null,
        },
      ],
    };
    fetchMock.mockResolvedValue(json(body));
    function P() {
      const p = usePricing();
      return <p>{p.status === "ready" ? String(p.data.plans[0]?.firstRenewalDate) : p.status}</p>;
    }
    render(<P />);
    await waitFor(() => expect(screen.getByText("null")).toBeInTheDocument());
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/pricing");
  });
});

describe("crisis fallback contract", () => {
  it("matches the numbers and names in content/crisis-resources.json", () => {
    const file = resolve(import.meta.dirname, "../../../content/crisis-resources.json");
    const content = JSON.parse(readFileSync(file, "utf8")) as {
      resources: { id: string; name: string; phone: string; description: string }[];
    };
    const expected = content.resources.slice(0, CRISIS_FALLBACK.length);
    expect(CRISIS_FALLBACK).toEqual(expected);
  });
});
