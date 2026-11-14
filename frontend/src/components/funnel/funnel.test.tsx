import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import quizFixture from "../../test/fixtures/quiz.json";
import { ActionBar } from "./ActionBar";
import { DocumentGrid } from "./DocumentGrid";
import { Interstitial } from "./Interstitial";
import { MultiChoice } from "./MultiChoice";
import { ProgressBar } from "./ProgressBar";
import { QuestionFrame } from "./QuestionFrame";
import { ScaleInput } from "./ScaleInput";
import { SingleChoice } from "./SingleChoice";

interface RawQ {
  id: string;
  title: string;
  subtitle?: string;
  healthData: boolean;
  options: { id: string; label: string }[];
  max: number;
  min?: number;
  minLabel: string;
  maxLabel: string;
  body: string;
  states: { id: string; label: string }[];
  rows: { id: string; label: string; hint: string }[];
}
const questions = (quizFixture as unknown as { questions: RawQ[] }).questions;
function q(id: string): RawQ {
  const found = questions.find((x) => x.id === id);
  if (!found) throw new Error(id);
  return found;
}
function at<T>(items: T[], i: number): T {
  const item = items[i];
  if (item === undefined) throw new Error(`no item ${i}`);
  return item;
}

const fetchSpy = vi.fn();
vi.stubGlobal("fetch", fetchSpy);
afterEach(() => expect(fetchSpy).not.toHaveBeenCalled());

function Single() {
  const question = q("q1_recipient");
  const [v, setV] = useState<string | null>(null);
  return (
    <QuestionFrame title={question.title}>
      <SingleChoice legend={question.title} options={question.options} value={v} onChange={setV} />
    </QuestionFrame>
  );
}

function Multi({ id = "q5_changes" }: { id?: string }) {
  const question = q(id);
  const [v, setV] = useState<string[]>([]);
  return (
    <QuestionFrame title={question.title} subtitle={question.subtitle} healthNote={question.healthData ? "Saved privately." : undefined}>
      <MultiChoice legend={question.title} options={question.options} max={question.max} value={v} onChange={setV} />
    </QuestionFrame>
  );
}

function Grid() {
  const question = q("q10_documents");
  const [v, setV] = useState<Record<string, string>>({});
  return (
    <>
      <DocumentGrid rows={question.rows} states={question.states} value={v} onChange={setV} />
      <ActionBar primary={{ label: "Continue", onClick: () => undefined, disabled: Object.keys(v).length < question.rows.length }} />
    </>
  );
}

function Scale() {
  const question = q("q11_confidence");
  const [v, setV] = useState<number | null>(null);
  return (
    <ScaleInput legend={question.title} min={question.min ?? 1} max={question.max} minLabel={question.minLabel} maxLabel={question.maxLabel} value={v} onChange={setV} />
  );
}

describe("QuestionFrame", () => {
  it("renders the focus-target heading, subtitle and health note only when given", () => {
    render(<Multi />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveAttribute("data-funnel-heading");
    expect(screen.getByText("Saved privately.")).toBeInTheDocument();
  });
  it("has no health note for a non-health question", () => {
    render(<Multi id="q9_worries" />);
    expect(screen.queryByText("Saved privately.")).toBeNull();
  });
  it("is axe clean", async () => {
    const { container } = render(<Single />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("SingleChoice", () => {
  it("renders every option of a real question and selects by mouse", async () => {
    render(<Single />);
    const options = q("q1_recipient").options;
    expect(screen.getAllByRole("radio")).toHaveLength(options.length);
    await userEvent.click(screen.getByRole("radio", { name: at(options, 1).label }));
    expect(screen.getByRole("radio", { name: at(options, 1).label })).toBeChecked();
  });
  it("moves with arrow keys inside the radio group", async () => {
    render(<Single />);
    const options = q("q1_recipient").options;
    await userEvent.click(screen.getByRole("radio", { name: at(options, 0).label }));
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("radio", { name: at(options, 1).label })).toBeChecked();
  });
  it("shows an error", () => {
    render(<SingleChoice legend="L" options={[{ id: "a", label: "A" }]} value={null} onChange={() => undefined} error="Pick one." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Pick one.");
  });
  it("is axe clean with a selection", async () => {
    const { container } = render(<Single />);
    await userEvent.click(at(screen.getAllByRole("radio"), 0));
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("MultiChoice", () => {
  it("toggles with Space", async () => {
    render(<Multi />);
    const first = at(screen.getAllByRole("checkbox"), 0);
    first.focus();
    await userEvent.keyboard(" ");
    expect(first).toBeChecked();
    await userEvent.keyboard(" ");
    expect(first).not.toBeChecked();
  });
  it("enforces max 3 and announces it", async () => {
    render(<Multi />);
    const boxes = screen.getAllByRole("checkbox").filter((b) => !(b as HTMLInputElement).value.startsWith("none"));
    const fourth = at(boxes, 3);
    for (const b of boxes.slice(0, 3)) await userEvent.click(b);
    await userEvent.click(fourth);
    expect(fourth).not.toBeChecked();
    expect(fourth).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("status")).toHaveTextContent("up to 3");
  });
  it("exclusive none clears the others and announces it, and choosing another drops none", async () => {
    render(<Multi />);
    const boxes = screen.getAllByRole("checkbox");
    const [b0, b1] = [at(boxes, 0), at(boxes, 1)];
    await userEvent.click(b0);
    await userEvent.click(screen.getByRole("checkbox", { name: "None of these yet" }));
    expect(b0).not.toBeChecked();
    expect(screen.getByRole("status")).toHaveTextContent("cleared");
    await userEvent.click(b1);
    expect(screen.getByRole("checkbox", { name: "None of these yet" })).not.toBeChecked();
    expect(b1).toBeChecked();
  });
  it("is axe clean", async () => {
    const { container } = render(<Multi />);
    await userEvent.click(at(screen.getAllByRole("checkbox"), 0));
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("DocumentGrid", () => {
  it("keeps Continue aria-disabled until every row has a state", async () => {
    render(<Grid />);
    const rows = q("q10_documents").rows;
    const cont = screen.getByRole("button", { name: "Continue" });
    expect(cont).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(cont);
    for (let i = 0; i < rows.length; i++) {
      expect(cont).toHaveAttribute("aria-disabled", "true");
      const group = at(screen.getAllByRole("group"), i);
      await userEvent.click(within(group).getAllByRole("radio")[0] as HTMLElement);
    }
    expect(cont).not.toHaveAttribute("aria-disabled");
  });
  it("renders one group per row with hints and three states", () => {
    render(<Grid />);
    const rows = q("q10_documents").rows;
    expect(screen.getAllByRole("group")).toHaveLength(rows.length);
    expect(screen.getAllByRole("radio")).toHaveLength(rows.length * q("q10_documents").states.length);
    expect(screen.getByText(at(rows, 0).hint)).toBeInTheDocument();
  });
  it("is axe clean", async () => {
    const { container } = render(<Grid />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("ScaleInput", () => {
  it("shows five numbered radios and announces the end labels through the group description", async () => {
    render(<Scale />);
    const question = q("q11_confidence");
    expect(screen.getAllByRole("radio")).toHaveLength(5);
    expect(screen.getByRole("group")).toHaveAccessibleDescription(new RegExp(`${question.minLabel}.*${question.maxLabel}`));
    await userEvent.click(screen.getByRole("radio", { name: "4" }));
    expect(screen.getByRole("radio", { name: "4" })).toBeChecked();
  });
  it("is axe clean", async () => {
    const { container } = render(<Scale />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("Interstitial, ProgressBar, ActionBar", () => {
  it("renders an interstitial from a real card and ignores the speaker", async () => {
    const card = q("reassure_1");
    const { container } = render(<Interstitial title={card.title} body={card.body} />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(card.title);
    expect(screen.getByText(card.body)).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });
  it("progress exposes value text", async () => {
    const { container } = render(<ProgressBar current={3} total={11} label="3 of 11" />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuetext", "3 of 11");
    expect(await axe(container)).toHaveNoViolations();
  });
  it("action bar: enabled fires, aria-disabled does not, secondary fires", async () => {
    const go = vi.fn();
    const skip = vi.fn();
    const { rerender, container } = render(<ActionBar primary={{ label: "Continue", onClick: go }} secondary={{ label: "Skip", onClick: skip }} />);
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await userEvent.click(screen.getByRole("button", { name: "Skip" }));
    expect(go).toHaveBeenCalledTimes(1);
    expect(skip).toHaveBeenCalledTimes(1);
    rerender(<ActionBar primary={{ label: "Continue", onClick: go, disabled: true }} />);
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(go).toHaveBeenCalledTimes(1);
    expect(await axe(container)).toHaveNoViolations();
  });
});
