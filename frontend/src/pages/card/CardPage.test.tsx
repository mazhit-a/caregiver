import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import snapshot from "../../test/fixtures/app/card-public.json";
import { installFakeApi, type FakeApi } from "../../test/fakeApi";
import { cardTitle } from "../../content/app/publicCard";
import { CardLayout } from "./CardLayout";
import CardPage from "./CardPage";

const NodeRequest = Request;
class TestRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal ? { ...init, signal: undefined } : init);
  }
}

const SECRET = "secretCardId123";
let api: FakeApi;

function memoryStorage(): Storage {
  const data = new Map<string, string>();
  return {
    get length() {
      return data.size;
    },
    clear: () => data.clear(),
    getItem: (k) => data.get(k) ?? null,
    key: (i) => [...data.keys()][i] ?? null,
    removeItem: (k) => void data.delete(k),
    setItem: (k, v) => void data.set(k, v),
  };
}

function mount(): void {
  const router = createMemoryRouter(
    [{ element: <CardLayout />, children: [{ path: "/card/:cardId", element: <CardPage /> }] }],
    { initialEntries: [`/card/${SECRET}`] },
  );
  render(<RouterProvider router={router} />);
}

beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  vi.stubGlobal("localStorage", memoryStorage());
  vi.stubGlobal("sessionStorage", memoryStorage());
});
afterEach(() => {
  api?.restore();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("public care card page", () => {
  it("renders every snapshot field, sends no token and makes one request only", async () => {
    api = installFakeApi({ publicCard: "ok" });
    const logs = vi.spyOn(console, "log");
    mount();
    expect(await screen.findByRole("heading", { level: 1, name: cardTitle(snapshot.displayName) })).toBeInTheDocument();
    for (const t of [...snapshot.enjoys, ...snapshot.calms, ...snapshot.avoid, ...snapshot.phrases, snapshot.rhythm]) {
      expect(screen.getByText(t)).toBeInTheDocument();
    }
    expect(screen.getByText(/Updated Jan 6, 2026/)).toBeInTheDocument();
    expect(screen.getByText(/Shared by Alex/)).toBeInTheDocument();
    for (const h of snapshot.helplines) {
      expect(screen.getByRole("link", { name: h.phone })).toHaveAttribute("href", `tel:${h.phone.replace(/[^\d+]/g, "")}`);
      expect(screen.getByText(h.description)).toBeInTheDocument();
    }
    expect(screen.getByRole("link", { name: "555-0100" })).toHaveAttribute("href", "tel:5550100");
    expect(screen.getByText("Try to avoid")).toBeInTheDocument();

    expect(api.calls).toEqual([{ method: "GET", path: `/cards/${SECRET}`, token: null }]);
    expect(document.title).not.toContain(SECRET);
    expect(document.title).toContain("What works with Margaret");
    expect(logs).not.toHaveBeenCalled();
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(document.querySelector('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
    expect(document.querySelector('meta[name="referrer"]')).toHaveAttribute("content", "no-referrer");
    expect(await axe(document.body)).toHaveNoViolations();
  });

  it("sends no token even when a session token is stored", async () => {
    localStorage.setItem("pcn_session_token", "stored-token");
    api = installFakeApi({ publicCard: "ok" });
    mount();
    await screen.findByRole("heading", { level: 1, name: /What works with/ });
    expect(api.calls.every((c) => c.token === null && c.path.startsWith("/cards/"))).toBe(true);
    expect(localStorage.getItem("pcn_session_token")).toBe("stored-token");
  });

  it.each([
    ["missing", "We can't find this card"],
    ["revoked", "This card is no longer shared"],
    ["rate_limited", "Too many people opened this link"],
  ] as const)("shows the %s state", async (state, heading) => {
    api = installFakeApi({ publicCard: state });
    mount();
    expect(await screen.findByRole("heading", { level: 1, name: heading })).toBeInTheDocument();
    expect(document.body.textContent).not.toContain(SECRET);
    expect(await axe(document.body)).toHaveNoViolations();
  });

  it("offers retry on a network failure and recovers", async () => {
    api = installFakeApi({ publicCard: "ok", networkDown: true });
    mount();
    const retry = await screen.findByRole("button", { name: "Try again" });
    api.scenario.networkDown = false;
    await userEvent.click(retry);
    expect(await screen.findByRole("heading", { level: 1, name: /What works with Margaret/ })).toBeInTheDocument();
  });

  it("shows a retry on a 5xx", async () => {
    api = installFakeApi({ publicCard: "ok" });
    api.injectError("GET", `/cards/${SECRET}`, 500, "server_error");
    mount();
    expect(await screen.findByRole("heading", { level: 1, name: "We couldn't load this card" })).toBeInTheDocument();
    expect(await axe(document.body)).toHaveNoViolations();
  });
});

describe("static checks", () => {
  it("print CSS hides the print button and goes black and white", () => {
    const css = readFileSync(resolve(__dirname, "CardPage.module.css"), "utf-8");
    const print = css.slice(css.indexOf("@media print"));
    expect(print).toContain(".print { display: none; }");
    expect(print).toContain("#000");
    expect(print).toContain("#fff");
  });

  it("nginx keeps the card id out of access logs", () => {
    const conf = readFileSync(resolve(__dirname, "../../../nginx.conf"), "utf-8");
    const block = /location \/card\/ \{([^}]*)\}/.exec(conf)?.[1] ?? "";
    expect(block).toContain("access_log off;");
    expect(block).toContain('Cache-Control "no-store"');
  });
});
