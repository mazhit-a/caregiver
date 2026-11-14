import { useReducer, useRef, useEffect } from "react";
import { PracticeRound } from "../../components/practice/PracticeRound";
import { GOAL_LABELS, PRACTICE_SCRIPT, scoreOf, type PracticeVariant } from "../../content/practiceScript";
import { PRACTICE_COPY } from "../../content/practice";
import styles from "./PracticePage.module.css";

interface State {
  variant: PracticeVariant;
  round: number;
  picks: readonly number[];
  /** Option picked in the current round, or null. */
  current: number | null;
  finished: boolean;
}

type Action = { type: "variant"; variant: PracticeVariant } | { type: "pick"; index: number } | { type: "next" } | { type: "restart" };

const ROUNDS = 3;
const initial = (variant: PracticeVariant): State => ({ variant, round: 0, picks: [], current: null, finished: false });

export function practiceReducer(state: State, action: Action): State {
  switch (action.type) {
    case "variant":
      return initial(action.variant);
    case "restart":
      return initial(state.variant);
    case "pick":
      return state.current === null ? { ...state, current: action.index } : state;
    case "next": {
      if (state.current === null) return state;
      const picks = [...state.picks, state.current];
      return picks.length >= ROUNDS
        ? { ...state, picks, current: null, finished: true }
        : { ...state, picks, round: state.round + 1, current: null };
    }
  }
}

const VARIANTS: readonly { id: PracticeVariant; label: string }[] = [
  { id: "in_person", label: "In person" },
  { id: "phone", label: "On the phone" },
];

export function PracticeDemo() {
  const [state, dispatch] = useReducer(practiceReducer, "in_person", initial);
  const { variant, round: roundIndex, current, finished, picks } = state;
  const script = PRACTICE_SCRIPT[variant];
  const round = script[roundIndex] ?? script[0];
  if (!round) throw new Error("practice script is empty");
  const nextRef = useRef<HTMLButtonElement>(null);
  const summaryRef = useRef<HTMLHeadingElement>(null);
  const roundRef = useRef<HTMLParagraphElement>(null);

  // After a pick, move focus to the Next button; after the last round, to the summary; after "Next round", to the round header.
  useEffect(() => {
    if (current !== null) nextRef.current?.focus();
  }, [current]);
  useEffect(() => {
    if (finished) summaryRef.current?.focus();
  }, [finished]);
  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    if (roundIndex > 0 && current === null && !finished) roundRef.current?.focus();
  }, [roundIndex, current, finished]);

  const scoreAt = (i: number): number => {
    const pick = picks[i];
    const option = pick === undefined ? undefined : script[i]?.options[pick];
    return option ? scoreOf(option) : 0;
  };

  return (
    <div className={styles.demo}>
      <div className={styles.demoHead}>
        <h2 className={styles.demoTitle}>{PRACTICE_COPY.demo.title}</h2>
        <div role="group" aria-label={PRACTICE_COPY.demo.toggleLabel} className={styles.toggle}>
          {VARIANTS.map((v) => (
            <button
              key={v.id}
              type="button"
              aria-pressed={state.variant === v.id}
              className={styles.toggleButton}
              onClick={() => dispatch({ type: "variant", variant: v.id })}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>
      <ul className={styles.chips} aria-label="The three steps">
        {GOAL_LABELS.map((label) => (
          <li key={label} className={styles.chip}>
            {label}
          </li>
        ))}
      </ul>

      {state.finished ? (
        <div className={styles.summary}>
          <h3 ref={summaryRef} tabIndex={-1} className={styles.summaryTitle}>
            Your practice
          </h3>
          <div className={styles.scores}>
            <div className={styles.scoreFirst}>
              <p className={styles.scoreLabel}>First try</p>
              <p className={styles.scoreValue}>{scoreAt(0)} of 3</p>
            </div>
            <div className={styles.scoreLast}>
              <p className={styles.scoreLabel}>Last try</p>
              <p className={styles.scoreValue}>{scoreAt(ROUNDS - 1)} of 3</p>
            </div>
          </div>
          <p className={styles.body}>{PRACTICE_COPY.demo.savedNote}</p>
          <button type="button" className={styles.secondary} onClick={() => dispatch({ type: "restart" })}>
            Practice again
          </button>
        </div>
      ) : (
        <div className={styles.roundWrap}>
          <p ref={roundRef} tabIndex={-1} className={styles.roundNumber}>
            Round {state.round + 1} of 3
          </p>
          <PracticeRound
            key={`${state.variant}-${state.round}`}
            round={round}
            picked={state.current}
            onPick={(index) => dispatch({ type: "pick", index })}
            afterFeedback={
              <button ref={nextRef} type="button" className={styles.primary} onClick={() => dispatch({ type: "next" })}>
                {state.round === ROUNDS - 1 ? "See your practice" : "Next round"}
              </button>
            }
          />
        </div>
      )}
      <p className={styles.footnote}>{PRACTICE_COPY.demo.footnote}</p>
    </div>
  );
}
