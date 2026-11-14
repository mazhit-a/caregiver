import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { axe } from "vitest-axe";
import CoursePage from "./CoursePage";

function renderPage() {
  return render(
    <MemoryRouter>
      <main>
        <CoursePage />
      </main>
    </MemoryRouter>,
  );
}

describe("CoursePage", () => {
  it("renders one h1, Module 1 with five numbered lessons and eight module cards", () => {
    renderPage();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    const lessons = screen.getByRole("list", { name: "Module 1 lessons" });
    expect(lessons.tagName).toBe("OL");
    expect(within(lessons).getAllByRole("listitem")).toHaveLength(5);
    expect(within(lessons).getAllByText("8 min")).toHaveLength(3);
    const cards = screen.getAllByRole("heading", { level: 3 });
    expect(cards).toHaveLength(8);
  });

  it("labels unbuilt modules Coming soon or Coming later and lists five quick guides", () => {
    renderPage();
    expect(screen.getAllByText("Coming soon")).toHaveLength(6);
    expect(screen.getAllByText("Coming later")).toHaveLength(2);
    expect(screen.getByText("If Mom goes missing")).toBeInTheDocument();
    expect(screen.getByText("After a fall")).toBeInTheDocument();
  });

  it("has an alt on the hero image and a CTA to the quiz", () => {
    renderPage();
    expect(screen.getByRole("img", { name: "Ollie reading a book" })).toHaveAttribute("loading", "eager");
    expect(screen.getByRole("link", { name: "Get Mom’s plan" })).toHaveAttribute("href", "/quiz");
  });

  it("has no axe violations", async () => {
    const { container } = renderPage();
    expect(await axe(container)).toHaveNoViolations();
  });
});
