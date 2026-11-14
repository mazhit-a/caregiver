import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { HOME_ROUND } from "../../content/practiceScript";
import { FeedbackCard } from "./FeedbackCard";
import { GoalChips } from "./GoalChips";
import { PracticeRound } from "./PracticeRound";

function option(index: number) {
  const found = HOME_ROUND.options[index];
  if (!found) throw new Error("missing option");
  return found;
}

function Harness() {
  const [picked, setPicked] = useState<number | null>(null);
  return (
    <PracticeRound
      round={HOME_ROUND}
      picked={picked}
      onPick={setPicked}
      afterFeedback={
        <button type="button" onClick={() => setPicked(null)}>
          Try another answer
        </button>
      }
    />
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("GoalChips", () => {
  it("states met and not-yet in text", () => {
    render(<GoalChips goals={[true, false, true]} />);
    const items = screen.getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Notice the feeling: met");
    expect(items[1]).toHaveTextContent("Reassure: not yet");
    expect(items[2]).toHaveTextContent("Offer something to do: met");
  });
});

describe("FeedbackCard", () => {
  it("shows score, tip and Mom's reply", async () => {
    const { container } = render(
      <FeedbackCard option={{ goals: [true, true, false], tip: "A tip.", mom: "Mom says hi." }} />,
    );
    expect(screen.getByText("Ollie’s feedback")).toBeInTheDocument();
    expect(screen.getByText("2 of 3")).toBeInTheDocument();
    expect(screen.getByText("A tip.")).toBeInTheDocument();
    expect(screen.getByText("Mom says hi.")).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("PracticeRound", () => {
  it("shows options, then feedback after a pick, and can reset", async () => {
    const user = userEvent.setup();
    const { container } = render(<Harness />);
    expect(screen.getByText("What would you say?")).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();

    await user.click(screen.getByRole("button", { name: option(2).text }));
    expect(screen.queryByText("What would you say?")).not.toBeInTheDocument();
    expect(screen.getByText("3 of 3")).toBeInTheDocument();
    expect(screen.getByText(option(2).mom)).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();

    await user.click(screen.getByRole("button", { name: "Try another answer" }));
    expect(screen.getByText("What would you say?")).toBeInTheDocument();
  });

  it("announces feedback in a polite live region", async () => {
    const user = userEvent.setup();
    const { container } = render(<Harness />);
    const live = container.querySelector("[aria-live='polite']");
    expect(live).not.toBeNull();
    await user.click(screen.getByRole("button", { name: option(0).text }));
    expect(within(live as HTMLElement).getByText("0 of 3")).toBeInTheDocument();
  });

  it("never calls fetch", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    const user = userEvent.setup();
    render(<Harness />);
    for (const option of HOME_ROUND.options) {
      await user.click(screen.getByRole("button", { name: option.text }));
      await user.click(screen.getByRole("button", { name: "Try another answer" }));
    }
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
