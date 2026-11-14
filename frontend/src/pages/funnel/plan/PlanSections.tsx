import { Link } from "react-router";
import type { PlanModule, PlanPreview, QuickGuide } from "../../../api/funnelTypes";
import {
  moduleLessonsLabel,
  PLAN_PREVIEW,
  PROOF,
} from "../../../content/funnel";
import { quizQuestionRoute } from "../../../routes";
import styles from "./plan.module.css";

/** "What we heard": the API's sentences as one paragraph, plus the way back to the answers. */
export function WhatWeHeard({ sentences }: { sentences: string[] }) {
  return (
    <section className={styles.card} aria-labelledby="heard-title">
      <h2 id="heard-title" className={styles.h2}>
        {PLAN_PREVIEW.whatWeHeardTitle}
      </h2>
      <p className={styles.body}>{sentences.join(" ")}</p>
      <Link to={quizQuestionRoute("q1_recipient")} className={styles.textLink}>
        {PLAN_PREVIEW.editLink}
      </Link>
    </section>
  );
}

export function BeforeAfterCards({ value }: { value: PlanPreview["beforeAfter"] }) {
  return (
    <section className={styles.pair} aria-labelledby="ba-title">
      <h2 id="ba-title" className={styles.h2}>
        {PLAN_PREVIEW.beforeAfterTitle}
      </h2>
      <div className={styles.pairGrid}>
        <div className={styles.card}>
          <h3 className={styles.h3}>{PLAN_PREVIEW.beforeLabel}</h3>
          <p className={styles.body}>{value.before}</p>
        </div>
        <div className={styles.card}>
          <h3 className={styles.h3}>{PLAN_PREVIEW.afterLabel}</h3>
          <p className={styles.body}>{value.after}</p>
        </div>
      </div>
    </section>
  );
}

/** First-30-days modules (API order), the pace line and the "coming later" titles. */
export function First30Days({ modules, paceLabel }: { modules: PlanModule[]; paceLabel: string }) {
  const first = modules.filter((m) => m.inFirst30Days);
  const later = modules.filter((m) => m.status === "later");
  return (
    <section aria-labelledby="first30-title" className={styles.stack}>
      <h2 id="first30-title" className={styles.h2}>
        {PLAN_PREVIEW.first30Title}
      </h2>
      <p className={styles.body}>{paceLabel}</p>
      <ol className={styles.modules}>
        {first.map((m, i) => (
          <li key={m.id} className={i === 0 ? `${styles.module} ${styles.moduleFirst}` : styles.module}>
            <p className={styles.moduleMeta}>
              <span className={styles.number}>{i + 1}</span>
              {moduleLessonsLabel(m.lessons.length)}
            </p>
            <h3 className={styles.h3}>{m.title}</h3>
            <p className={styles.body}>{m.reason}</p>
            <p className={styles.lessons}>{m.lessons.map((l) => l.title).join(" · ")}</p>
          </li>
        ))}
      </ol>
      {later.length > 0 && (
        <p className={styles.body}>
          <strong>{PLAN_PREVIEW.laterTitle}:</strong> {later.map((m) => m.title).join(", ")}
        </p>
      )}
    </section>
  );
}

export function QuickGuides({ guides, highlightLabel }: { guides: QuickGuide[]; highlightLabel: string }) {
  return (
    <section aria-labelledby="guides-title" className={styles.stack}>
      <h2 id="guides-title" className={styles.h2}>
        {PLAN_PREVIEW.quickGuidesTitle}
      </h2>
      <p className={styles.body}>{PLAN_PREVIEW.quickGuidesNote}</p>
      <ul className={styles.chips}>
        {guides.map((g) => (
          <li key={g.id} className={g.highlight ? `${styles.chip} ${styles.chipOn}` : styles.chip}>
            {g.highlight ? `${g.title} · ${highlightLabel}` : g.title}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function WhyThisWorks() {
  return (
    <section aria-labelledby="proof-title" className={styles.stack}>
      <h2 id="proof-title" className={styles.h2}>
        {PROOF.title}
      </h2>
      <ul className={styles.proof}>
        {PROOF.items.map((item) => (
          <li key={item.source}>
            <p className={styles.body}>{item.text}</p>
            <p className={styles.source}>{item.source}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
