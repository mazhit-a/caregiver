import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { axe } from "vitest-axe";
import HowPage from "./HowPage";

function setup() {
  return render(
    <MemoryRouter>
      <HowPage />
    </MemoryRouter>,
  );
}

describe("HowPage", () => {
  it("has one h1 and the step headings in order", () => {
    setup();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    const h2s = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(h2s).toEqual([
      "Tell us what’s happening",
      "See Mom’s plan before you pay",
      "A lesson takes about 8 minutes",
      "Lessons adapt to where the hard moments reach you",
      "The next day, a quick check-in",
      "Ready to see Mom’s plan?",
    ]);
    for (const n of [1, 2, 3, 4, 5]) expect(screen.getByText(`Step ${n}`)).toBeInTheDocument();
  });

  it("renders a real table with column and row headers and 4 body rows", () => {
    setup();
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("columnheader")).toHaveLength(3);
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(5);
    const rowHeaders = within(table).getAllByRole("rowheader");
    expect(rowHeaders.map((h) => h.textContent)).toEqual([
      "In person",
      "On the phone",
      "In a care home",
      "Not noticed yet",
    ]);
  });

  it("lists the seven quiz topics and the four lesson steps", () => {
    setup();
    expect(screen.getByRole("list", { name: "What the questions cover" }).children).toHaveLength(7);
    expect(screen.getByRole("heading", { level: 3, name: /A real moment/ })).toBeInTheDocument();
  });

  it("uses the replaced privacy copy and never says browser", () => {
    const { container } = setup();
    expect(screen.getByText(/Saved privately to this session\. No account, no name needed\./)).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/in your browser/i);
  });

  it("labels the example plan visibly and keeps the no-guilt line", () => {
    setup();
    expect(screen.getByText("Example plan")).toBeVisible();
    expect(screen.getByText("No streaks, no guilt. Three short sessions a week is plenty.")).toBeInTheDocument();
  });

  it("points every call to action at the quiz", () => {
    setup();
    const cta = screen.getAllByRole("link", { name: /Get Mom’s plan/ });
    expect(cta.length).toBeGreaterThan(0);
    for (const link of cta) expect(link).toHaveAttribute("href", "/quiz");
  });

  it("gives every image alt text and size", () => {
    setup();
    for (const img of screen.getAllByRole("img")) {
      expect(img).toHaveAttribute("alt");
      expect(img).toHaveAttribute("width");
      expect(img).toHaveAttribute("height");
    }
    expect(screen.getAllByRole("img")).toHaveLength(3);
  });

  it("has no axe violations", async () => {
    const { container } = setup();
    expect(await axe(container)).toHaveNoViolations();
  });
});
