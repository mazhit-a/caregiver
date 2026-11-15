import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { AppDataProvider } from "../../../../api/AppDataProvider";
import type { ContentScreen as ContentData, IntroScreen as IntroData, Lesson } from "../../../../api/appTypes";
import { clearToken, setToken } from "../../../../api/session";
import { type FakeApi, installFakeApi } from "../../../../test/fakeApi";
import { signIn } from "../../../../test/fakeApp/core";
import lessonPhone from "../../../../test/fixtures/app/lesson24-phone.json";
import { ContentScreen } from "./ContentScreen";
import { IntroScreen } from "./IntroScreen";

const NodeRequest = Request;
class TestRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal ? { ...init, signal: undefined } : init);
  }
}

let api: FakeApi;
beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  clearToken();
  api = installFakeApi();
  setToken(signIn(api));
});
afterEach(() => {
  api.restore();
  vi.unstubAllGlobals();
});

const lesson = lessonPhone as unknown as Lesson;
const byId = <T,>(id: string): T => lesson.screens.find((s) => s.id === id) as unknown as T;
const noop = () => undefined;
const common = { lesson, entry: undefined, remember: noop, reload: () => Promise.resolve(true) };

const everything: ContentData = {
  id: "all",
  type: "content",
  part: "Part one",
  title: "All the blocks",
  body: ["First paragraph.", "Second paragraph."],
  image: "ollie-explaining",
  items: [
    { title: "Worry", text: "Something is coming." },
    { title: "Lost", text: "No clock." },
  ],
  steps: [
    { n: 1, title: "Notice", text: "Say the feeling." },
    { n: 2, title: "Reassure", text: "Keep it short." },
  ],
  dodont: { do: ["Say less."], dont: ["Argue."] },
  examples: [{ text: "I will tell you when.", why: "It takes the job off her." }],
  note: { line1: "Saturday.", line2: "I will call." },
  keyIdea: "The feeling stays.",
  tip: "One calm line.",
};

async function renderContent(screenData: ContentData) {
  const utils = render(
    <AppDataProvider>
      <ContentScreen screen={screenData} {...common} />
    </AppDataProvider>,
  );
  return utils;
}

describe("IntroScreen", () => {
  it("shows the part, title, body, bullets and the pose beside the title", () => {
    const data = byId<IntroData>("intro");
    const { container } = render(<IntroScreen screen={{ ...data, part: "Start" }} {...common} />);
    expect(screen.getByRole("heading", { level: 2, name: data.title })).toBeInTheDocument();
    expect(screen.getByText("Start")).toBeInTheDocument();
    expect(within(screen.getByRole("list")).getAllByRole("listitem")).toHaveLength(data.bullets.length);
    expect(container.textContent).not.toMatch(/[{}]/);
  });

  it("renders no image for an unknown pose and for ollie-calm-none", () => {
    const data = byId<IntroData>("intro");
    const { container, rerender } = render(<IntroScreen screen={{ ...data, image: "ollie-calm-none" }} {...common} />);
    expect(container.querySelector("img")).toBeNull();
    rerender(<IntroScreen screen={{ ...data, image: "ollie-idea" }} {...common} />);
    expect(container.querySelector("img")).toBeNull();
    rerender(<IntroScreen screen={{ ...data, image: "ollie-reading" }} {...common} />);
    expect(container.querySelector("img")).toHaveAttribute("alt", "");
  });

  it("has no axe violations", async () => {
    const { container } = render(<IntroScreen screen={byId<IntroData>("intro")} {...common} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("ContentScreen blocks", () => {
  it("renders items as a list of cards", async () => {
    await renderContent({ ...everything, steps: null, dodont: null, examples: null, note: null });
    const lists = screen.getAllByRole("list");
    expect(lists.some((l) => within(l).queryAllByRole("listitem").some((i) => i.textContent?.includes("Worry")))).toBe(true);
  });

  it("renders steps as an ordered list with numbers", async () => {
    const { container } = await renderContent(everything);
    const ol = container.querySelector("ol");
    expect(ol).not.toBeNull();
    expect(within(ol as HTMLElement).getAllByRole("listitem")).toHaveLength(2);
    expect(ol?.textContent).toContain("Notice");
  });

  it("renders do and skip boxes with headings from the app copy", async () => {
    await renderContent(everything);
    expect(await screen.findByRole("heading", { level: 3, name: /Try/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: /Skip/ })).toBeInTheDocument();
    expect(screen.getByText("Say less.")).toBeInTheDocument();
    expect(screen.getByText("Argue.")).toBeInTheDocument();
  });

  it("renders example bubbles, the sticky note, the key idea and Ollie's tip", async () => {
    await renderContent(everything);
    expect(screen.getByText("I will tell you when.")).toBeInTheDocument();
    expect(screen.getByText("It takes the job off her.")).toBeInTheDocument();
    expect(screen.getByText("Saturday.")).toBeInTheDocument();
    expect(screen.getByText("I will call.")).toBeInTheDocument();
    expect(screen.getByText("The feeling stays.")).toBeInTheDocument();
    expect(screen.getByText("One calm line.")).toBeInTheDocument();
    expect(screen.getByText(/Ollie’s tip:/)).toBeInTheDocument();
  });

  it("keeps the prototype order: body, image, items, steps, do/skip, examples, note, key idea, tip", async () => {
    const { container } = await renderContent(everything);
    await screen.findByRole("heading", { level: 3, name: /Try/ });
    const text = container.textContent ?? "";
    const order = [
      "All the blocks",
      "First paragraph.",
      "Worry",
      "Notice",
      "Say less.",
      "I will tell you when.",
      "Saturday.",
      "The feeling stays.",
      "One calm line.",
    ].map((t) => text.indexOf(t));
    expect(order.every((i) => i >= 0)).toBe(true);
    expect([...order].sort((a, b) => a - b)).toEqual(order);
    const pose = container.querySelector("img");
    expect(pose?.nextElementSibling?.tagName).toBe("H2");
  });

  it("renders only the blocks that are present", async () => {
    const { container } = await renderContent({
      ...everything,
      items: null,
      steps: null,
      dodont: null,
      examples: null,
      note: null,
      keyIdea: null,
      tip: null,
      image: null,
    });
    expect(container.querySelectorAll("ul, ol")).toHaveLength(0);
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getAllByText(/paragraph\./)).toHaveLength(2);
  });

  it("renders every real content screen of the phone lesson with no raw braces and no axe violations", async () => {
    for (const s of lesson.screens.filter((x) => x.type === "content")) {
      const { container, unmount } = await renderContent(s as ContentData);
      await waitFor(() => expect(container.querySelector("h2")).not.toBeNull());
      expect(container.textContent).not.toMatch(/[{}]/);
      expect(container.querySelector("[style]")).toBeNull();
      expect(await axe(container)).toHaveNoViolations();
      unmount();
    }
  });

  it("has no axe violations with every block present", async () => {
    const { container } = await renderContent(everything);
    await screen.findByRole("heading", { level: 3, name: /Try/ });
    expect(await axe(container)).toHaveNoViolations();
  });
});
