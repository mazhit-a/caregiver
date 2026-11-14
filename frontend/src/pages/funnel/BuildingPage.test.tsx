import { readFileSync } from "node:fs";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { createSession } from "../../api/funnel";
import { clearToken, getToken } from "../../api/session";
import { routes } from "../../router";
import { type FakeApi, installFakeApi } from "../../test/fakeApi";
import copy from "../../test/fixtures/funnel-copy.json";
import previewA from "../../test/fixtures/preview-a.json";
import quizAnswered from "../../test/fixtures/quiz-answered.json";

const NodeRequest = Request;
class TestRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal ? { ...init, signal: undefined } : init);
  }
}

let api: FakeApi;
beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  clearToken();
});
afterEach(() => api?.restore());

async function setup(answered = true) {
  api = installFakeApi();
  await createSession();
  const state = api.sessions.get(getToken() ?? "");
  if (state && answered) {
    state.answers = { ...(quizAnswered as { answers: Record<string, unknown> }).answers };
  }
  const router = createMemoryRouter(routes, { initialEntries: ["/quiz/building"] });
  const utils = render(<RouterProvider router={router} />);
  return { router, ...utils };
}

const completes = () => api.calls.filter((c) => c.path === "/quiz/complete").length;
const ready = () => screen.findByRole("heading", { level: 1, name: copy.loader.title });

describe("BuildingPage", () => {
  it("completes once, shows exactly the API lines and goes on only by button", async () => {
    const { router, container } = await setup();
    await ready();
    expect(completes()).toBe(1);
    const list = screen.getByRole("status", { name: copy.loader.title });
    const items = Array.from(list.querySelectorAll("li")).map((li) => li.textContent);
    expect(items).toEqual(previewA.loaderLines);
    expect(router.state.location.pathname).toBe("/quiz/building");
    expect(await axe(container)).toHaveNoViolations();
    await userEvent.click(screen.getByRole("button", { name: copy.planPreview.cta }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/your-plan"));
  });

  it("sends quiz_incomplete to the first missing question", async () => {
    const { router } = await setup(false);
    await waitFor(() => expect(router.state.location.pathname).toMatch(/^\/quiz\/q\d/));
    expect(completes()).toBe(1);
  });

  it("shows an error with Try again and retries complete", async () => {
    api = installFakeApi();
    await createSession();
    const state = api.sessions.get(getToken() ?? "");
    if (state) state.answers = { ...(quizAnswered as { answers: Record<string, unknown> }).answers };
    api.injectError("POST", "/quiz/complete", 500, "server_error");
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/quiz/building"] })} />);
    const retry = await screen.findByRole("button", { name: "Try again" });
    await userEvent.click(retry);
    await ready();
    expect(completes()).toBe(2);
  });

  it("sends a locked quiz to /today and a lost session to the quiz intro", async () => {
    api = installFakeApi();
    await createSession();
    api.injectError("POST", "/quiz/complete", 409, "quiz_locked");
    const router = createMemoryRouter(routes, { initialEntries: ["/quiz/building"] });
    render(<RouterProvider router={router} />);
    await waitFor(() => expect(router.state.location.pathname).toBe("/today"));
  });

  it("drops the stagger under reduced motion (CSS)", () => {
    const css = readFileSync("src/pages/funnel/BuildingPage.module.css", "utf8");
    expect(css).toMatch(/prefers-reduced-motion: reduce\)[\s\S]*animation: none/);
  });
});
