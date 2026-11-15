/**
 * Fake of lesson 1 as the 24-screen lesson (batch 4, C2): served from the
 * `lesson24-*` fixtures (recaptured from the real backend in C7). Active only with `scenario.lesson24`.
 * Correctness lives here, not in the browser: `answerkey-m1_l1.json` is the test-only answer key
 * the real server keeps on its side. Quiz, builder and reset picks are kept as ids only.
 */
import { appFixture } from "./fixtures";
import {
  type FakeAppSession,
  type FakeReq,
  type FakeRes,
  type FakeRoute,
  registerFakeArea,
  route,
} from "./registry";

type Json = Record<string, unknown>;

interface Screen {
  id: string;
  type: string;
  options?: { id: string }[];
  answers?: { id: string }[];
  groups?: { options: { id: string }[] }[];
}
interface LessonBody extends Json {
  screens: Screen[];
  progress: Json;
}
interface Key {
  quiz: Record<string, { correct: boolean; feedback: string }[]>;
  builder: Record<string, { correct: boolean; text: string }[][]>;
  reset: Record<string, { label: string; plan: string }[]>;
  scenario: Record<string, { verdict: string; feedback: string }[]>;
}

const ok = (body: unknown): FakeRes => ({ status: 200, body });
const fail = (status: number, name: string): FakeRes => ({ status, body: appFixture(name) });
const key = (): Key => appFixture<Key>("answerkey-m1_l1");

function state(session: FakeAppSession): { variant: string | null; picks: Record<string, string>; step?: number } {
  if (!("v2" in session.app)) session.app["v2"] = { variant: null, picks: {} };
  return session.app["v2"] as { variant: string | null; picks: Record<string, string>; step?: number };
}

const active = (req: FakeReq, id: string | undefined): boolean => req.scenario.lesson24 && id === "m1_l1";

function lessonBody(session: FakeAppSession): LessonBody {
  const s = state(session);
  const name = s.variant === null ? "lesson24-initial" : `lesson24-${s.variant}`;
  const lesson = appFixture<LessonBody>(name);
  if (s.step !== undefined) lesson.progress = { ...lesson.progress, step: s.step };
  return lesson;
}

function answer(req: FakeReq): FakeRes {
  const session = req.session as FakeAppSession;
  const s = state(session);
  const lesson = lessonBody(session);
  const screen = lesson.screens.find((x) => x.id === req.body["screenId"]);
  const value = req.body["value"];
  const bad = (): FakeRes => fail(422, "err-422-lesson-answer");
  if (!screen) return bad();
  const done = (type: string, result: Json): FakeRes => ok({ screenId: screen.id, type, result });
  switch (screen.type) {
    case "setup": {
      if (!screen.options?.some((o) => o.id === value)) return bad();
      s.variant = value as string;
      return done("setup", { variant: s.variant });
    }
    case "scenario": {
      const at = screen.answers?.findIndex((a) => a.id === value) ?? -1;
      const row = s.variant === null ? undefined : key().scenario[s.variant]?.[at];
      if (!row) return bad();
      s.picks[screen.id] = value as string;
      return done("scenario", {
        answerId: value, verdict: row.verdict, feedback: row.feedback, savePhrase: row.verdict === "best",
      });
    }
    case "quiz": {
      const rows = key().quiz[screen.id];
      const at = screen.options?.findIndex((o) => o.id === value) ?? -1;
      const row = rows?.[at];
      if (!rows || !row) return bad();
      s.picks[screen.id] = value as string;
      const right = rows.findIndex((r) => r.correct);
      return done("quiz", {
        optionId: value, correct: row.correct, correctOptionId: screen.options?.[right]?.id, feedback: row.feedback,
      });
    }
    case "builder": {
      const groups = key().builder[screen.id];
      const picks = Array.isArray(value) ? (value as unknown[]) : null;
      if (!groups || !screen.groups || !picks || picks.length !== groups.length) return bad();
      const rows = picks.map((p, g) => groups[g]?.[screen.groups?.[g]?.options.findIndex((o) => o.id === p) ?? -1]);
      if (rows.some((r) => r === undefined)) return bad();
      const checked = rows as { correct: boolean; text: string }[];
      return done("builder", {
        reply: checked.map((r) => r.text).join(" "),
        allCorrect: checked.every((r) => r.correct),
        groups: checked.map((r) => ({ correct: r.correct })),
      });
    }
    case "reset": {
      const at = screen.options?.findIndex((o) => o.id === value) ?? -1;
      const row = key().reset[screen.id]?.[at];
      if (!row) return bad();
      s.picks[screen.id] = value as string;
      return done("reset", { optionId: value, text: row.plan });
    }
    case "plan": {
      const plan = appFixture<Json & { result: { ifThen: Json } }>("answer-plan");
      const resetId = s.picks["you"];
      const reset = key().reset["you"]?.find((_, i) => `r${i + 1}` === resetId)?.plan ?? null;
      return ok({ ...plan, screenId: screen.id, result: { ...plan.result, ifThen: { ...plan.result.ifThen, reset } } });
    }
    case "wrap":
      return ok({ ...appFixture<Json>("answer-wrap"), screenId: screen.id });
    default:
      return bad();
  }
}

/** A route that answers only for lesson 1 while `scenario.lesson24` is on; otherwise it falls through to core. */
function lesson24Route(
  method: string,
  suffix: string,
  handler: (req: FakeReq) => FakeRes,
): FakeRoute {
  const inner = route(method, new RegExp(`^/lessons/([^/]+)${suffix}$`), (req, [id]) =>
    active(req, id) ? handler(req) : { status: 0 },
  );
  return (req) => {
    const res = inner(req);
    return res && res.status === 0 ? undefined : res;
  };
}

registerFakeArea("lessonV2", [
  lesson24Route("GET", "", (req) => ok(lessonBody(req.session as FakeAppSession))),
  lesson24Route("POST", "/answers", answer),
  lesson24Route("PUT", "/progress", (req) => {
    const session = req.session as FakeAppSession;
    const step = req.body["step"];
    const count = lessonBody(session).screens.length;
    if (typeof step !== "number" || !Number.isInteger(step) || step < 0 || step >= count) {
      return fail(422, "err-422-progress");
    }
    state(session).step = step;
    return ok({ ...appFixture<Json>("progress-put"), step });
  }),
]);
