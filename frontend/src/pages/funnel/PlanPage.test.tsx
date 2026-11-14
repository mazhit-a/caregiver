import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { completeQuiz, createSession } from "../../api/funnel";
import { clearToken, getToken } from "../../api/session";
import { routes } from "../../router";
import { type FakeApi, installFakeApi } from "../../test/fakeApi";
import copy from "../../test/fixtures/funnel-copy.json";
import giftB from "../../test/fixtures/gift-b.json";
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

async function setup(q3: string | null) {
  api = installFakeApi();
  await createSession();
  const state = api.sessions.get(getToken() ?? "");
  if (state && q3) {
    state.answers = { ...(quizAnswered as { answers: Record<string, unknown> }).answers, q3_situation: q3 };
    await completeQuiz();
  }
  const router = createMemoryRouter(routes, { initialEntries: ["/your-plan"] });
  const utils = render(<RouterProvider router={router} />);
  return { router, ...utils };
}

const ready = () => screen.findByRole("heading", { level: 1, name: copy.planPreview.title });
const moduleTitles = () =>
  within(screen.getByRole("region", { name: "Your first 30 days" }))
    .getAllByRole("heading", { level: 3 })
    .map((h) => h.textContent);

describe("PlanPage", () => {
  it("persona B: heard text, modules in API order with reasons, no placeholders, axe clean", async () => {
    const { container } = await setup("recent");
    await ready();
    expect(
      screen.getByText(
        "Mom was diagnosed in the last few months. Mom lives far away. You're handling most of it alone, and you work full-time. What worries you most: knowing what to say and legal papers and money.",
      ),
    ).toBeInTheDocument();
    expect(moduleTitles()).toEqual([
      "Talking with Mom",
      "While she can still decide",
      "Hard moments",
    ]);
    expect(screen.getByText(/Because some of Mom's key papers are missing/)).toBeInTheDocument();
    expect(screen.getByText("5 short lessons")).toBeInTheDocument();
    expect(screen.getByText(/Coming later:/)).toBeInTheDocument();
    expect(screen.getByText("About 10 minutes a lesson, 4 lessons a week")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Why this works" })).toBeInTheDocument();
    expect(container.textContent).not.toContain("{");
    expect(await axe(container)).toHaveNoViolations();
  });

  it("persona C: Safe home second and the hospital chip highlighted with the content label", async () => {
    await setup("changing");
    await ready();
    expect(moduleTitles()[1]).toMatch(/home/i);
    expect(
      screen.getByText(`After a hospital stay · ${copy.planPreview.highlightLabel}`),
    ).toBeInTheDocument();
    expect(screen.getByText("A sudden change in confusion")).toBeInTheDocument();
  });

  it("persona A: Before the diagnosis second and Dad wording", async () => {
    await setup("noticing");
    await ready();
    expect(moduleTitles()[1]).toMatch(/Before the diagnosis/i);
    expect(screen.getByText("If Dad goes missing")).toBeInTheDocument();
  });

  it("gift card shows API title and intro and links to the sheet; bar goes to the paywall", async () => {
    const { router } = await setup("recent");
    await ready();
    const card = await screen.findByRole("region", { name: giftB.title });
    expect(within(card).getByText(giftB.intro)).toBeInTheDocument();
    expect(within(card).getByRole("link", { name: "Download free sheet" })).toHaveAttribute(
      "href",
      "/your-plan/gift",
    );
    expect(screen.getByRole("link", { name: "Change my answers" })).toHaveAttribute(
      "href",
      "/quiz/q1_recipient",
    );
    await userEvent.click(screen.getByRole("button", { name: copy.planPreview.cta }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/paywall"));
  });

  it("a failing gift request shows an inline retry and does not block the page", async () => {
    api = installFakeApi();
    await createSession();
    const state = api.sessions.get(getToken() ?? "");
    if (state) state.answers = { ...(quizAnswered as { answers: Record<string, unknown> }).answers };
    await completeQuiz();
    api.injectError("GET", "/plan/gift", 500, "server_error");
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/your-plan"] })} />);
    await ready();
    const retry = await screen.findByRole("button", { name: "Try again" });
    expect(screen.getByRole("button", { name: copy.planPreview.cta })).toBeInTheDocument();
    await userEvent.click(retry);
    expect(await screen.findByRole("link", { name: "Download free sheet" })).toBeInTheDocument();
  });

  it("402 no_plan goes to the quiz resume", async () => {
    const { router } = await setup(null);
    await waitFor(() => expect(router.state.location.pathname).toMatch(/^\/quiz/));
  });

  it("a preview failure shows Try again and retries", async () => {
    api = installFakeApi();
    await createSession();
    const state = api.sessions.get(getToken() ?? "");
    if (state) state.answers = { ...(quizAnswered as { answers: Record<string, unknown> }).answers };
    await completeQuiz();
    api.injectError("GET", "/plan/preview", 500, "server_error");
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/your-plan"] })} />);
    await userEvent.click(await screen.findByRole("button", { name: "Try again" }));
    await ready();
  });
});
