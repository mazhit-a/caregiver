import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { axe } from "vitest-axe";
import { CtaBand } from "./CtaBand";
import { Faq } from "./Faq";
import { FeatureRow } from "./FeatureRow";
import { ImageFigure } from "./ImageFigure";
import { NumberedSteps } from "./NumberedSteps";
import { PageHero } from "./PageHero";
import { Section } from "./Section";

function renderInRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("Section", () => {
  it("renders every variant with its children", () => {
    for (const variant of ["plain", "butter", "plum", "muted"] as const) {
      const { unmount } = render(<Section variant={variant}>content {variant}</Section>);
      expect(screen.getByText(`content ${variant}`)).toBeInTheDocument();
      unmount();
    }
  });
});

describe("ImageFigure", () => {
  it("sets size, async decoding and lazy loading", () => {
    render(<ImageFigure src="/x.webp" alt="A picture" width={10} height={20} />);
    const img = screen.getByRole("img", { name: "A picture" });
    expect(img).toHaveAttribute("width", "10");
    expect(img).toHaveAttribute("height", "20");
    expect(img).toHaveAttribute("loading", "lazy");
    expect(img).toHaveAttribute("decoding", "async");
  });

  it("requires alt text by type", () => {
    // @ts-expect-error alt is required
    render(<ImageFigure src="/x.webp" width={1} height={1} />);
  });
});

describe("PageHero, FeatureRow, NumberedSteps, CtaBand", () => {
  it("renders with no axe violations and links the CTA to the quiz", async () => {
    const { container } = renderInRouter(
      <main>
        <PageHero
          eyebrow="Eyebrow"
          title="Hero title"
          lead="Lead text"
          image={{ src: "/h.webp", alt: "Hero art", width: 400, height: 500 }}
        >
          <p>Note</p>
        </PageHero>
        <Section variant="butter">
          <FeatureRow title="Feature" visual={<ImageFigure src="/f.webp" alt="Feature art" width={5} height={5} />} reverse>
            <p>Feature text</p>
          </FeatureRow>
          <NumberedSteps
            steps={[
              { title: "One", text: "First" },
              { title: "Two", text: "Second" },
              { title: "Three", text: "Third" },
            ]}
          />
          <CtaBand title="Ready?" text="Go on." />
        </Section>
      </main>,
    );
    expect(screen.getByRole("heading", { level: 1, name: "Hero title" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Feature" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getByRole("link", { name: "Get Mom’s plan" })).toHaveAttribute("href", "/quiz");
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("Faq", () => {
  const items = [
    { question: "First?", answer: "Answer one." },
    { question: "Second?", answer: "Answer two." },
  ];

  it("summary is a tab stop and toggles its answer", async () => {
    // jsdom does not turn Enter/Space on <summary> into a click as browsers do,
    // so the toggle itself is exercised with a click on the focused summary.
    const user = userEvent.setup();
    render(<Faq items={items} />);
    const summary = screen.getByText("First?").closest("summary");
    const details = screen.getByText("First?").closest("details");
    expect(details).not.toHaveAttribute("open");
    await user.tab();
    expect(summary).toHaveFocus();
    await user.click(summary as HTMLElement);
    expect(details).toHaveAttribute("open");
    expect(screen.getByText("Answer one.")).toBeVisible();
    await user.tab();
    expect(screen.getByText("Second?").closest("summary")).toHaveFocus();
    await user.click(summary as HTMLElement);
    expect(details).not.toHaveAttribute("open");
  });

  it("has no axe violations", async () => {
    const { container } = render(<Faq items={items} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
