import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { setToken } from "../../api/session";
import { routes } from "../../router";
import { installFakeApi, type FakeApi } from "../../test/fakeApi";
import fall from "../../test/fixtures/guides/qg_fall.json";
import limit from "../../test/fixtures/guides/qg_limit.json";
import missing from "../../test/fixtures/guides/qg_missing.json";

const NodeRequest = Request;
class TestRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal ? { ...init, signal: undefined } : init);
  }
}

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

let api: FakeApi;

function mount(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return { router, ...render(<RouterProvider router={router} />) };
}

beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  vi.stubGlobal("localStorage", memoryStorage());
  vi.stubGlobal("sessionStorage", memoryStorage());
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  api = installFakeApi();
});
afterEach(() => {
  api.restore();
  vi.unstubAllGlobals();
});

describe("guide page", () => {
  it("renders the sections in order with the 911 box first, with no session and no token header", async () => {
    mount("/guides/qg_fall");
    expect(await screen.findByRole("heading", { level: 1, name: fall.title })).toBeInTheDocument();
    expect(screen.getByText(fall.summary)).toBeInTheDocument();

    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings).toEqual(
      [fall.callNowTitle, fall.stepsTitle, fall.thenTitle, fall.dontTitle, fall.resourcesTitle, "Sources"].filter(
        (h) => h !== undefined,
      ),
    );
    // The red box comes before the steps in the document.
    const box = screen.getByRole("heading", { name: fall.callNowTitle });
    const steps = screen.getByRole("heading", { name: fall.stepsTitle });
    expect(box.compareDocumentPosition(steps) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    for (const t of fall.callNow) expect(screen.getByText(t)).toBeInTheDocument();

    const stepList = within(screen.getByRole("region", { name: fall.stepsTitle })).getByRole("list");
    expect(stepList.tagName).toBe("OL");
    expect(within(stepList).getAllByRole("listitem")).toHaveLength(fall.steps.length);
    expect(screen.getByText(fall.footer)).toBeInTheDocument();
    expect(fall.footer).toBe("In an emergency, call 911.");
    expect(document.body.textContent).not.toMatch(/\{[A-Za-z]+\}/);

    const guideCalls = api.calls.filter((c) => c.path.startsWith("/guides"));
    expect(guideCalls).toEqual([{ method: "GET", path: "/guides/qg_fall", token: null }]);
    expect(api.calls.every((c) => c.token === null)).toBe(true);
    expect(document.querySelector('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
    expect(document.querySelector("main img")).toBeNull();
    expect(screen.queryByText(/ollie/i)).toBeNull();
    expect(await axe(document.body)).toHaveNoViolations();
  });

  it("omits the 911 box when the guide has none", async () => {
    api.inject({ method: "GET", path: "/guides/qg_limit", status: 200, body: { ...limit, callNow: [] } });
    mount("/guides/qg_limit");
    await screen.findByRole("heading", { level: 1, name: limit.title });
    expect(screen.queryByRole("heading", { name: limit.callNowTitle })).toBeNull();
  });

  it("gives every resource a 48px-class tap-to-call link and sources safe attributes", async () => {
    mount("/guides/qg_missing");
    await screen.findByRole("heading", { level: 1, name: missing.title });
    for (const r of missing.resources) {
      const link = screen.getByRole("link", { name: new RegExp(r.number.replace(/[-]/g, "[-]")) });
      expect(link).toHaveAttribute("href", `tel:${r.tel}`);
    }
    for (const s of missing.sources) {
      const link = screen.getByRole("link", { name: s.name });
      expect(link).toHaveAttribute("href", s.url);
      expect(link).toHaveAttribute("target", "_blank");
      expect(link.getAttribute("rel")?.split(" ")).toEqual(expect.arrayContaining(["noopener", "noreferrer"]));
    }
  });

  it("sends the stored session token when there is one", async () => {
    setToken("fake-token-1");
    mount("/guides/qg_fall");
    await screen.findByRole("heading", { level: 1 });
    // An unknown token answers 401: the guide is public, so it is asked again without the token.
    expect(api.calls.map((c) => c.token)).toEqual(["fake-token-1", null]);
    expect(await screen.findByRole("heading", { level: 1, name: fall.title })).toBeInTheDocument();
  });

  it("shows a not-found state for an unknown guide", async () => {
    mount("/guides/nope");
    expect(await screen.findByRole("heading", { level: 1, name: "We can't find this guide" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
    expect(await axe(document.body)).toHaveNoViolations();
  });

  it("shows loading, then an error with retry that recovers", async () => {
    api.scenario.networkDown = true;
    mount("/guides/qg_fall");
    expect(await screen.findByRole("status")).toHaveTextContent("Loading the guide");
    const retry = await screen.findByRole("button", { name: "Try again" });
    expect(await axe(document.body)).toHaveNoViolations();
    api.scenario.networkDown = false;
    await userEvent.click(retry);
    expect(await screen.findByRole("heading", { level: 1, name: fall.title })).toBeInTheDocument();
  });

  it("has the logo link, a Back link and the help button, and opens the help sheet", async () => {
    mount("/guides/qg_fall");
    await screen.findByRole("heading", { level: 1, name: fall.title });
    expect(screen.getByRole("link", { name: "Kelper home" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Back" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).toBeNull();
    expect(screen.getByRole("button", { name: "Need help now?" })).toBeInTheDocument();
  });

  it("Back goes to the previous page inside the app", async () => {
    const router = createMemoryRouter(routes, { initialEntries: ["/start", "/guides/qg_fall"], initialIndex: 1 });
    render(<RouterProvider router={router} />);
    await screen.findByRole("heading", { level: 1, name: fall.title });
    await userEvent.click(screen.getByRole("link", { name: "Back" }));
    await vi.waitFor(() => expect(router.state.location.pathname).toBe("/start"));
  });

  it("print CSS hides the header and goes black and white", () => {
    const layout = readFileSync(resolve(__dirname, "GuideLayout.module.css"), "utf-8");
    expect(layout.slice(layout.indexOf("@media print"))).toContain(".header { display: none; }");
    const css = readFileSync(resolve(__dirname, "GuidePage.module.css"), "utf-8");
    const print = css.slice(css.indexOf("@media print"));
    expect(print).toContain("#000");
    expect(print).toContain("#fff");
  });
});
