import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { PRACTICE_SCRIPT, scoreOf, type PracticeVariant } from "../../content/practiceScript";
import PracticePage from "./PracticePage";

type Round = (typeof PRACTICE_SCRIPT)["phone"][number];

function get<T>(items: readonly T[], i: number): T {
  const item = items[i];
  if (item === undefined) throw new Error(`missing item ${i}`);
  return item;
}

function setup() {
  return render(
    <MemoryRouter>
      <PracticePage />
    </MemoryRouter>,
  );
}

async function play(variant: PracticeVariant, pickIndex: (round: number) => number) {
  const user = userEvent.setup();
  const rounds = PRACTICE_SCRIPT[variant] as readonly Round[];
  for (let r = 0; r < 3; r++) {
    expect(screen.getByText(`Round ${r + 1} of 3`)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: get(get(rounds, r).options, pickIndex(r)).text }));
    const next = screen.getByRole("button", { name: r === 2 ? "See your practice" : "Next round" });
    expect(next).toHaveFocus();
    await user.click(next);
  }
}

afterEach(() => vi.restoreAllMocks());

describe("PracticePage", () => {
  it("has one h1 and the privacy statement", () => {
    setup();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByText(/Not stored: the conversation isn’t saved/)).toBeInTheDocument();
    expect(screen.getByText(/Preview with set answers/)).toBeInTheDocument();
  });

  for (const variant of ["in_person", "phone"] as const) {
    it(`runs three rounds and summarises first and last try (${variant})`, async () => {
      const fetchSpy = vi.spyOn(globalThis, "fetch");
      setup();
      if (variant === "phone") await userEvent.click(screen.getByRole("button", { name: "On the phone" }));
      const rounds = PRACTICE_SCRIPT[variant] as readonly Round[];
      // first round: worst option (index 0), last round: best option (index 1 or 2 with 3 goals)
      const best = (r: number) => get(rounds, r).options.findIndex((o) => scoreOf(o) === 3);
      await play(variant, (r) => (r === 0 ? 0 : best(r)));
      expect(screen.getByRole("heading", { name: "Your practice" })).toHaveFocus();
      expect(screen.getByText("First try").nextElementSibling).toHaveTextContent("0 of 3");
      expect(screen.getByText("Last try").nextElementSibling).toHaveTextContent("3 of 3");
      expect(screen.getByText(/best phrase is saved to Mom’s page/)).toBeInTheDocument();
      expect(fetchSpy).not.toHaveBeenCalled();
      await userEvent.click(screen.getByRole("button", { name: "Practice again" }));
      expect(screen.getByText("Round 1 of 3")).toBeInTheDocument();
    });
  }

  it("switching variant resets the demo", async () => {
    const user = userEvent.setup();
    setup();
    await user.click(screen.getByRole("button", { name: get(get(PRACTICE_SCRIPT.in_person, 0).options, 0).text }));
    await user.click(screen.getByRole("button", { name: "Next round" }));
    expect(screen.getByText("Round 2 of 3")).toBeInTheDocument();
    const phone = screen.getByRole("button", { name: "On the phone" });
    await user.click(phone);
    expect(phone).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Round 1 of 3")).toBeInTheDocument();
    expect(screen.getByText(get(PRACTICE_SCRIPT.phone, 0).line)).toBeInTheDocument();
  });

  it("is axe clean", async () => {
    const { container } = setup();
    expect(await axe(container)).toHaveNoViolations();
  });
});
