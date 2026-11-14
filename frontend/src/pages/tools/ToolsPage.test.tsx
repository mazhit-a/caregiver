import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { axe } from "vitest-axe";
import ToolsPage from "./ToolsPage";

function setup() {
  return render(
    <MemoryRouter>
      <ToolsPage />
    </MemoryRouter>,
  );
}

describe("ToolsPage", () => {
  it("has one h1 and the section headings", () => {
    setup();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    for (const name of [
      "Mom’s page",
      "A care card for whoever is with her",
      "One page for the doctor",
      "Free: phrases that calm Mom",
      "Get your free phrase sheet",
    ]) {
      expect(screen.getByRole("heading", { name })).toBeInTheDocument();
    }
  });

  it("labels the mocks as examples and keeps the not-medical note", () => {
    setup();
    expect(screen.getByText("Example care card")).toBeInTheDocument();
    expect(screen.getByText("Example visit sheet")).toBeInTheDocument();
    expect(screen.getAllByText("Family observations, not a medical assessment.").length).toBeGreaterThanOrEqual(2);
  });

  it("uses the session privacy copy, never 'in your browser'", () => {
    const { container } = setup();
    expect(screen.getByText(/Saved privately to this session/)).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/in your browser/i);
  });

  it("links the CTA to the quiz and gives images size and alt", () => {
    setup();
    expect(screen.getByRole("link", { name: "Get Mom’s plan" })).toHaveAttribute("href", "/quiz");
    const img = screen.getByRole("img", { name: "Ollie writing in a small notebook" });
    expect(img).toHaveAttribute("width", "482");
    expect(img).toHaveAttribute("height", "640");
  });

  it("has no axe violations", async () => {
    const { container } = setup();
    expect(await axe(container)).toHaveNoViolations();
  });
});
