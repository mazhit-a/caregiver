import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { HOME_ROUND } from "../../content/practiceScript";
import HomePage from "./HomePage";

const fetchMock = vi.fn<typeof fetch>();

function renderHome() {
  const router = createMemoryRouter([{ path: "/", element: <HomePage /> }]);
  return render(<RouterProvider router={router} />);
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("HomePage", () => {
  it("has the section headings in order", async () => {
    renderHome();
    const names = screen.getAllByRole("heading").map((h) => h.textContent?.replace(/^Step \d+: /, ""));
    const expected = [
      "Mom’s diagnosis came with a brochure. Here’s the plan.",
      "Try it: Mom asks again",
      "Meet Ollie, your guide",
      "From “what now?” to a plan in three steps",
      "Tell us what’s happening",
      "Get Mom’s plan",
      "Learn, practice, try it for real",
      "Practice the hard conversation before it happens",
      "A course that follows Mom, not a pile of articles",
      "What you learn, ready to share",
      "Works wherever Mom is",
      "Calm, honest and private",
      "We teach, not treat",
      "Your answers stay with you",
      "Clear terms",
      "Help is one tap away",
      "Questions",
      "Start with one calm step",
    ];
    expect(names).toEqual(expected);
  });

  it("runs the canned preview: scores 0, 1 and 3, then resets, with no fetch for it", async () => {
    renderHome();
    const callsBefore = fetchMock.mock.calls.length;
    const scores = [0, 1, 3];
    for (const [index, score] of scores.entries()) {
      const option = HOME_ROUND.options[index];
      if (!option) throw new Error("missing option");
      await userEvent.click(screen.getByRole("button", { name: option.text }));
      const feedback = document.querySelector<HTMLElement>("[aria-live=polite]");
      if (!feedback) throw new Error("missing feedback region");
      expect(within(feedback).getByText(`${score} of 3`)).toBeInTheDocument();
      expect(screen.getByText(option.tip)).toBeInTheDocument();
      expect(screen.getByText(option.mom)).toBeInTheDocument();
      await userEvent.click(screen.getByRole("button", { name: "Try another answer" }));
      expect(screen.getByRole("button", { name: option.text })).toBeInTheDocument();
    }
    expect(fetchMock.mock.calls.length).toBe(callsBefore);
  });

  it("shows no price, no pricing link and makes no API call", () => {
    const { container } = renderHome();
    expect(container.textContent).not.toMatch(/\$\d/);
    expect(screen.queryByRole("link", { name: "See plans" })).toBeNull();
    expect(container.querySelector("a[href='/pricing']")).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("opens FAQ items from the keyboard-reachable summary", async () => {
    renderHome();
    const summary = screen.getByText("What is Kelper?").closest("summary");
    expect(summary).not.toBeNull();
    const details = summary?.parentElement as HTMLDetailsElement;
    expect(details.open).toBe(false);
    await userEvent.click(summary as HTMLElement);
    expect(details.open).toBe(true);
  });

  it("uses the privacy replacement copy and never says 'in your browser'", async () => {
    const { container } = renderHome();
    expect(screen.getAllByText(/Saved privately to this session/).length).toBeGreaterThan(0);
    expect(container.textContent?.toLowerCase()).not.toContain("in your browser");
    expect(container.textContent?.toLowerCase()).not.toContain("this browser");
  });

  it("points every start link to the quiz and keeps the section links internal", async () => {
    renderHome();
    for (const link of screen.getAllByRole("link", { name: "Get Mom’s plan" })) {
      expect(link).toHaveAttribute("href", "/quiz");
    }
    const links: Record<string, string> = {
      "See how it works": "/how-it-works",
      "How practice works": "/practice",
      "See the course": "/course",
      "See the care tools": "/care-tools",
      "How lessons adapt": "/how-it-works",
    };
    for (const [name, href] of Object.entries(links)) {
      expect(screen.getByRole("link", { name })).toHaveAttribute("href", href);
    }
  });

  it("has alt text on both Ollie images and hides the decorative mocks", async () => {
    renderHome();
    expect(screen.getByAltText("Ollie, a sea otter in a lavender sweater, waving hello")).toHaveAttribute("loading", "lazy");
    expect(screen.getByAltText("Ollie pointing the way forward")).toBeInTheDocument();
    expect(screen.getByText("Your practice").closest("[aria-hidden=true]")).not.toBeNull();
    expect(screen.getByText("Start here").closest("[aria-hidden=true]")).not.toBeNull();
  });

  it("passes axe", async () => {
    const router = createMemoryRouter([{ path: "/", element: <main><HomePage /></main> }]);
    const { container } = render(<RouterProvider router={router} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  // context/ is git-ignored, so the design export only exists on a developer machine, not in CI.
  const designPath = resolve(import.meta.dirname, "../../../../context/design/kelper-landing/home/index.html");
  it.skipIf(!existsSync(designPath))("matches the design's visible text except for the allowed copy changes", async () => {
    const html = readFileSync(designPath, "utf8");
    const body = html.slice(html.indexOf("<main>"), html.indexOf("</main>"));
    const designText = new Set(
      body
        .replace(/<script[\s\S]*?<\/script>/g, "")
        .replace(/<br\s*\/?>/g, " ")
        .split(/<[^>]+>/)
        .map((t) => t.replace(/\s+/g, " ").trim())
        .filter((t) => t && !t.includes("{{")),
    );
    const { container } = renderHome();
    const rendered = container.textContent ?? "";
    const allowedMissing = new Set([
      // Shown only after a pick in the preview.
      "Ollie’s feedback",
      "Try another answer",
      "$14.99 for your first 4 weeks",
      "Then $29.99 every 4 weeks until you cancel. Cancel anytime in Settings.",
      // The "Clear prices" card was reworded: prices now appear only on the paywall.
      "See plans",
      "Clear prices",
      "The full price and renewal date before you pay. Cancel anytime in Settings.",
      "Quiz answers stay in your browser. No ad tracking in the quiz or the course.",
      "They stay in this browser. We don’t sell or share them, and there’s no ad tracking in the quiz or the course.",
    ]);
    const missing = [...designText].filter((t) => !rendered.includes(t) && !allowedMissing.has(t));
    expect(missing).toEqual([]);
  });
});
