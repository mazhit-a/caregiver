import { useCallback, useEffect, useRef, useState } from "react";
import { finishRoleplay, savePhrase, startRoleplay, submitTurn } from "../../../api/app";
import { useOutletContext } from "react-router";
import type {
  CoachPanel as CoachData,
  CrisisResource,
  FallbackScenario,
  PreviousTurn,
  RoleplayContext,
  RoleplayFinish,
  RoleplayStart,
} from "../../../api/appTypes";
import { useAppAction } from "../../../api/useAppRequest";
import { APP_ERROR_MESSAGES } from "../../../content/app/common";
import { COACH_COPY } from "../../../content/app/coach";
import { CaregiverBubble } from "../../../components/coach/CaregiverBubble";
import { FallbackScenarios } from "../../../components/coach/FallbackScenarios";
import { SafetyStop } from "../../../components/coach/SafetyStop";
import type { AppContext } from "../../../layout/app/appContext";
import { CoachPanel, type CoachPanelLabels } from "../../../components/coach/CoachPanel";
import { ParentBubble } from "../../../components/coach/ParentBubble";
import { ReplyBox } from "../../../components/coach/ReplyBox";
import { SummaryCard, type SummaryLabels } from "../../../components/coach/SummaryCard";
import type { CoachView } from "../../../components/coach/types";
import styles from "./roleplay.module.css";

export interface RoleplaySummaryText {
  title: string;
  bestPhraseLabel: string;
  saveButton: string;
  againButton: string;
}

export interface RoleplayRoomProps {
  lessonId: string;
  context: RoleplayContext;
  /** Called with the server summary when the learner continues (null when they leave early). */
  onDone: (finish: RoleplayFinish | null) => void;
  /** Summary wording from the lesson's roleplay screen; defaults are UI strings. */
  summaryText?: RoleplaySummaryText;
  /** When given, called once the summary shows and the room has no Continue of its own (the host's Continue moves on). */
  onSummary?: (finish: RoleplayFinish) => void;
}

type SaveState = "idle" | "saving" | "saved";

interface Turn {
  parent: string;
  reply: string;
  coach: CoachData;
}

const MAX_PREVIOUS = 3;

interface Safety {
  kind: "crisis" | "emergency";
  resources: CrisisResource[];
  emergencyText: string | null;
}

function toView(coach: CoachData): CoachView {
  return {
    score: coach.score,
    tip: coach.tip,
    betterPhrase: coach.betterPhrase,
    parentReaction: coach.parentReaction,
    goals: (Object.keys(coach.goals) as (keyof CoachData["goals"])[]).map((key) => ({
      key,
      label: COACH_COPY.goalLabels[key] ?? key,
      met: coach.goals[key],
    })),
  };
}

/**
 * The typed role-play. The transcript lives in this component's state only: it is sent to the
 * three role-play calls (and the chosen phrase to `POST /phrases`), never stored, logged or put
 * in a URL. Score and goals are shown exactly as the server returned them.
 */
export function RoleplayRoom({ lessonId, context, onDone, summaryText, onSummary }: RoleplayRoomProps) {
  const run = useAppAction();
  const [generation, setGeneration] = useState(0);
  const startedFor = useRef(-1);
  const [start, setStart] = useState<RoleplayStart | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [round, setRound] = useState(1);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [turnError, setTurnError] = useState<string | null>(null);
  const [safety, setSafety] = useState<Safety | null>(null);
  const [fallback, setFallback] = useState<FallbackScenario[] | null>(null);
  const shell = useOutletContext<AppContext | undefined>();
  const [finish, setFinish] = useState<RoleplayFinish | null>(null);
  const [finishing, setFinishing] = useState(false);
  const [finishError, setFinishError] = useState<string | null>(null);
  const [saves, setSaves] = useState<Record<string, SaveState>>({});
  const [saveError, setSaveError] = useState<Record<string, string | null>>({});
  const result = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (startedFor.current === generation) return;
    startedFor.current = generation;
    let live = true;
    void run(() => startRoleplay(lessonId, context)).then((outcome) => {
      if (!live) return;
      if (outcome.ok) setStart(outcome.data);
      else if (!outcome.handled) setStartError(APP_ERROR_MESSAGES[outcome.failure.kind]);
    });
    return () => {
      live = false;
    };
  }, [generation, lessonId, context, run]);

  const restart = useCallback(() => {
    setStart(null);
    setStartError(null);
    setRound(1);
    setTurns([]);
    setReply("");
    setBusy(false);
    setTurnError(null);
    setSafety(null);
    setFallback(null);
    setFinish(null);
    setFinishError(null);
    setSaves({});
    setSaveError({});
    setGeneration((g) => g + 1);
  }, []);

  useEffect(() => {
    if (finish) onSummary?.(finish);
  }, [finish, onSummary]);

  const tryRoundAgain = useCallback(() => {
    setTurns((all) => all.slice(0, round - 1));
    setReply("");
    setTurnError(null);
    setSaves((s) => ({ ...s, [`turn${round}`]: "idle" }));
    setSaveError((s) => ({ ...s, [`turn${round}`]: null }));
  }, [round]);

  const answered = turns.length >= round;
  useEffect(() => {
    if (answered) result.current?.focus();
  }, [answered]);

  if (startError) {
    return (
      <div className={styles["room"]}>
        <h2 className={styles["h"]}>{COACH_COPY.startFailedTitle}</h2>
        <p className={styles["text"]} role="alert">
          {COACH_COPY.aiDown}
        </p>
        <p className={styles["muted"]}>{startError}</p>
        <div className={styles["actions"]}>
          <button type="button" className={styles["primary"]} onClick={restart}>
            {COACH_COPY.tryAgain}
          </button>
          <button type="button" className={styles["secondary"]} onClick={() => onDone(null)}>
            {COACH_COPY.skipPractice}
          </button>
        </div>
      </div>
    );
  }
  if (!start) {
    return (
      <p className={styles["text"]} role="status">
        {COACH_COPY.starting}
      </p>
    );
  }

  const labels = start.labels;
  const text = summaryText ?? {
    title: COACH_COPY.summaryTitle,
    bestPhraseLabel: COACH_COPY.bestPhraseLabel,
    saveButton: COACH_COPY.saveShort,
    againButton: COACH_COPY.againButton,
  };

  async function send() {
    if (!start || busy || reply.trim() === "") return;
    const sent = reply;
    const current = start.rounds[round - 1];
    const previousTurns: PreviousTurn[] = turns.slice(-MAX_PREVIOUS).map((t) => ({
      parent: t.parent,
      caregiver: t.reply,
      score: t.coach.score,
    }));
    setBusy(true);
    setTurnError(null);
    const outcome = await run(() => submitTurn(start.runId, { round, reply: sent, previousTurns }));
    setBusy(false);
    if (!outcome.ok) {
      if (!outcome.handled) setTurnError(APP_ERROR_MESSAGES[outcome.failure.kind]);
      return;
    }
    const data = outcome.data;
    if (data.mode === "safety" && data.kind) {
      setReply("");
      setSafety({ kind: data.kind, resources: data.resources, emergencyText: data.emergencyText });
      return;
    }
    if (data.mode === "fallback" || data.runMode === "fallback") {
      setReply("");
      setFallback(data.fallbackScenarios);
      return;
    }
    if (!data.coach) {
      setFallback([]);
      return;
    }
    setTurns((all) => [...all, { parent: current?.line ?? "", reply: sent, coach: data.coach as CoachData }]);
    setReply("");
  }

  async function finishRun() {
    if (!start) return;
    setFinishing(true);
    setFinishError(null);
    const phrases = (fallback ? [] : turns)
      .filter((t) => t.coach.betterPhrase !== "")
      .map((t) => ({ reply: t.reply, betterPhrase: t.coach.betterPhrase }));
    const outcome = await run(() => finishRoleplay(start.runId, phrases));
    setFinishing(false);
    if (outcome.ok) setFinish(outcome.data);
    else if (!outcome.handled) setFinishError(APP_ERROR_MESSAGES[outcome.failure.kind]);
  }

  async function save(key: string, phrase: string) {
    if (saves[key] === "saving" || saves[key] === "saved") return;
    setSaves((s) => ({ ...s, [key]: "saving" }));
    setSaveError((s) => ({ ...s, [key]: null }));
    const outcome = await run(() => savePhrase({ text: phrase, source: "roleplay", lessonId }));
    if (outcome.ok) {
      setSaves((s) => ({ ...s, [key]: "saved" }));
      return;
    }
    setSaves((s) => ({ ...s, [key]: "idle" }));
    if (outcome.handled) return;
    const { failure } = outcome;
    setSaveError((s) => ({
      ...s,
      [key]:
        failure.kind === "validation" && failure.code === "phrase_limit_reached"
          ? COACH_COPY.phraseLimit
          : APP_ERROR_MESSAGES[failure.kind],
    }));
  }

  if (safety) {
    return (
      <div className={styles["room"]}>
        <SafetyStop
          kind={safety.kind}
          resources={safety.resources}
          emergencyText={safety.emergencyText}
          labels={{
            title: safety.kind === "crisis" ? COACH_COPY.crisisTitle : COACH_COPY.emergencyTitle,
            body: COACH_COPY.crisisBody,
            leave: COACH_COPY.leave,
            needHelp: COACH_COPY.needHelp,
            keepPracticing: COACH_COPY.keepPracticing,
            call: COACH_COPY.callLabel,
          }}
          onLeave={() => onDone(null)}
          onHelp={shell?.openHelp}
          onContinue={() => setSafety(null)}
        />
      </div>
    );
  }

  if (fallback && !finish) {
    if (fallback.length === 0) {
      return (
        <div className={styles["room"]}>
          <h2 className={styles["h"]}>{COACH_COPY.unavailableTitle}</h2>
          <p className={styles["text"]} role="status">
            {labels["aiDown"]}
          </p>
          <button type="button" className={styles["secondary"]} onClick={() => onDone(null)}>
            {COACH_COPY.skipPractice}
          </button>
        </div>
      );
    }
    return (
      <div className={styles["room"]}>
        <FallbackScenarios
          scenarios={fallback}
          finishing={finishing}
          finishError={finishError}
          onFinish={() => void finishRun()}
          onSkip={() => onDone(null)}
          labels={{
            aiDown: labels["aiDown"] ?? COACH_COPY.aiDown,
            intro: COACH_COPY.fallbackIntro,
            progress: COACH_COPY.fallbackProgress,
            verdicts: COACH_COPY.verdictLabels,
            next: COACH_COPY.fallbackNext,
            finish: COACH_COPY.fallbackFinish,
            finishing: COACH_COPY.fallbackFinishing,
            skip: COACH_COPY.skipPractice,
            tryAgain: COACH_COPY.fallbackRestart,
          }}
        />
      </div>
    );
  }

  if (finish && fallback) {
    return (
      <div className={styles["room"]}>
        <h2 className={styles["h"]}>{COACH_COPY.fallbackDoneTitle}</h2>
        <p className={styles["muted"]}>{labels["notSaved"]}</p>
        {!onSummary && (
          <div className={styles["actions"]}>
            <button type="button" className={styles["primary"]} onClick={() => onDone(finish)}>
              {COACH_COPY.continueButton}
            </button>
          </div>
        )}
      </div>
    );
  }

  if (finish) {
    const summaryLabels: SummaryLabels = {
      title: text.title,
      bestPhraseLabel: text.bestPhraseLabel,
      noBestPhrase: COACH_COPY.noBestPhrase,
      save: text.saveButton,
      saveBusy: COACH_COPY.saving,
      saved: COACH_COPY.savedShort,
      savedNote: COACH_COPY.savedNote,
      again: text.againButton,
      continueLabel: COACH_COPY.continueButton,
      privacy: COACH_COPY.privacyShort,
    };
    return (
      <div className={styles["room"]}>
        <SummaryCard
          firstVsLast={finish.firstVsLast}
          bestPhrase={finish.bestPhrase}
          labels={summaryLabels}
          saveState={saves["best"] ?? "idle"}
          saveError={saveError["best"] ?? null}
          onSave={() => finish.bestPhrase && void save("best", finish.bestPhrase)}
          onAgain={restart}
          onContinue={onSummary ? undefined : () => onDone(finish)}
        />
        <p className={styles["muted"]}>{labels["notSaved"]}</p>
      </div>
    );
  }

  const turn = answered ? turns[round - 1] : undefined;
  const line = start.rounds[round - 1];
  const lastRound = round >= start.roundsTotal;
  const panelLabels = (score: number): CoachPanelLabels => ({
    aiTag: COACH_COPY.aiTag,
    goals: COACH_COPY.goalsLabel,
    met: COACH_COPY.goalMet,
    notYet: COACH_COPY.goalNotYet,
    scoreLabel: COACH_COPY.scoreLabel,
    score: COACH_COPY.scoreOf(score),
    tip: COACH_COPY.tipLabel,
    tryLabel: COACH_COPY.tryLabel,
    save: COACH_COPY.saveShort,
    saveBusy: COACH_COPY.saving,
    saved: COACH_COPY.savedShort,
    savedNote: COACH_COPY.savedNote,
    tryAgain: COACH_COPY.tryAgain,
  });

  return (
    <div className={styles["room"]}>
      <p className={styles["muted"]}>{labels["partner"]}</p>
      <p className={styles["round"]}>{COACH_COPY.roundOf(round, start.roundsTotal)}</p>
      {line && <ParentBubble stage={line.stage} line={line.line} />}
      {turn ? (
        <div className={styles["result"]} ref={result} tabIndex={-1}>
          <CaregiverBubble text={turn.reply} label={COACH_COPY.youSaid} />
          <CoachPanel
            coach={toView(turn.coach)}
            labels={panelLabels(turn.coach.score)}
            saveState={saves[`turn${round}`] ?? "idle"}
            saveError={saveError[`turn${round}`] ?? null}
            onSave={() => void save(`turn${round}`, turn.coach.betterPhrase)}
            onTryAgain={tryRoundAgain}
          />
          {finishError && (
            <p className={styles["error"]} role="alert">
              {finishError}
            </p>
          )}
          {lastRound ? (
            <button type="button" className={styles["primary"]} aria-disabled={finishing} onClick={() => !finishing && void finishRun()}>
              {finishing ? COACH_COPY.finishing : COACH_COPY.seeSummary}
            </button>
          ) : (
            <button
              type="button"
              className={styles["primary"]}
              onClick={() => {
                setRound((r) => r + 1);
                setTurnError(null);
              }}
            >
              {COACH_COPY.nextRound}
            </button>
          )}
        </div>
      ) : (
        <>
          <ReplyBox
            value={reply}
            onChange={setReply}
            onSend={() => void send()}
            busy={busy}
            max={COACH_COPY.replyMax}
            label={COACH_COPY.replyLabel}
            hint={COACH_COPY.replyHint}
            counter={COACH_COPY.counter(reply.length, COACH_COPY.replyMax)}
            sendLabel={COACH_COPY.send}
            busyLabel={COACH_COPY.sending}
          />
          {busy && (
            <p className={styles["muted"]} role="status">
              {labels["thinking"]}
            </p>
          )}
          {turnError && (
            <div role="alert" className={styles["errorBox"]}>
              <p className={styles["text"]}>{labels["aiDown"]}</p>
              <p className={styles["muted"]}>{turnError}</p>
              <div className={styles["actions"]}>
                <button type="button" className={styles["secondary"]} onClick={() => void send()}>
                  {COACH_COPY.tryAgain}
                </button>
                <button type="button" className={styles["secondary"]} onClick={() => onDone(null)}>
                  {COACH_COPY.skipPractice}
                </button>
              </div>
            </div>
          )}
        </>
      )}
      <p className={styles["muted"]}>{labels["notSaved"]}</p>
    </div>
  );
}
