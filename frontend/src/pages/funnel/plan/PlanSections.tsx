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
    <section className={styles.heard} aria-labelledby="heard-title">
      <div className={styles.heardHead}>
        <h2 id="heard-title" className={styles.heardTitle}>
          {PLAN_PREVIEW.whatWeHeardTitle}
        </h2>
        <Link to={quizQuestionRoute("q1_recipient")} className={styles.textLink}>
          {PLAN_PREVIEW.editLink}
        </Link>
      </div>
      <p className={styles.body}>{sentences.join(" ")}</p>
    </section>
  );
}

export function BeforeAfterCards({ value }: { value: PlanPreview["beforeAfter"] }) {
  return (
    <section className={styles.stack} aria-labelledby="ba-title">
      <h2 id="ba-title" className={styles.h2}>
        {PLAN_PREVIEW.beforeAfterTitle}
      </h2>
      <div className={styles.pair}>
        <div className={styles.pairCard}>
          <h3 className={styles.pairLabel}>{PLAN_PREVIEW.beforeLabel}</h3>
          <p className={styles.pairText}>{value.before}</p>
        </div>
        <div className={`${styles.pairCard} ${styles.pairCardAfter}`}>
          <h3 className={styles.pairLabel}>{PLAN_PREVIEW.afterLabel}</h3>
          <p className={styles.pairText}>{value.after}</p>
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
      <p className={styles.small}>{paceLabel}</p>
      <ol className={styles.modules}>
        {first.map((m, i) => (
          <li key={m.id} className={i === 0 ? `${styles.module} ${styles.moduleFirst}` : styles.module}>
            <div className={styles.moduleHead}>
              <span className={styles.number}>{i + 1}</span>
              <h3 className={styles.moduleTitle}>{m.title}</h3>
              <span className={styles.count}>{moduleLessonsLabel(m.lessons.length)}</span>
            </div>
            <p className={styles.reason}>{m.reason}</p>
            <p className={styles.lessons}>{m.lessons.map((l) => l.title).join(" · ")}</p>
          </li>
        ))}
      </ol>
      {later.length > 0 && (
        <p className={styles.small}>
          {PLAN_PREVIEW.laterTitle}: {later.map((m) => m.title).join(", ")}
        </p>
      )}
    </section>
  );
}

export function QuickGuides({ guides, highlightLabel }: { guides: QuickGuide[]; highlightLabel: string }) {
  return (
    <section aria-labelledby="guides-title" className={styles.guides}>
      <h2 id="guides-title" className={styles.h2Small}>
        {PLAN_PREVIEW.quickGuidesTitle}
      </h2>
      <p className={styles.small}>{PLAN_PREVIEW.quickGuidesNote}</p>
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
      <h2 id="proof-title" className={styles.h2Small}>
        {PROOF.title}
      </h2>
      <ul className={styles.proof}>
        {PROOF.items.map((item) => (
          <li key={item.source}>
            <p className={styles.proofText}>{item.text}</p>
            <p className={styles.source}>{item.source}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
