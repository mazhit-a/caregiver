import { Link } from "react-router";
import { getSkills } from "../../../api/app";
import type { Skills } from "../../../api/appTypes";
import { useAppRequest } from "../../../api/useAppRequest";
import { APP_COMMON, APP_ERROR_MESSAGES } from "../../../content/app/common";
import {
  CONFIDENCE_LABELS,
  CONFIDENCE_ORDER,
  SKILLS_COPY,
  SKILLS_COUNT_LABELS,
  roleplayLine,
  scenarioLine,
  unlockLine,
} from "../../../content/app/skills";
import { formatDate } from "../../../format/date";
import { Seo, pageTitle } from "../../../layout/Seo";
import { lessonRoute } from "../../../routes";
import styles from "./SkillsPage.module.css";

const MAX_RATING = 5;


function Bar({ value, start }: { value: number; start?: boolean }) {
  return (
    <span className={styles.track} aria-hidden="true">
      <span className={`${start ? styles.fillStart : styles.fill} ${styles[`w${value}`] ?? ""}`} />
    </span>
  );
}

function Row({ name, value, start }: { name: string; value: number; start?: boolean }) {
  return (
    <div className={styles.row}>
      <span className={styles.rowName}>{name}</span>
      <Bar value={value} start={start} />
      <span className={styles.value}>{`${value} of ${MAX_RATING}`}</span>
    </div>
  );
}

function Confidence({ data }: { data: Skills["confidence"] }) {
  const { day0, first, latest } = data;
  if (day0 === null && !first && !latest) return null;
  const ids = CONFIDENCE_ORDER.filter((id) => first?.[id] !== undefined || latest?.[id] !== undefined);
  return (
    <section className={styles.card} aria-labelledby="skills-confidence">
      <h2 className={styles.cardTitle} id="skills-confidence">
        {SKILLS_COPY.confidenceTitle}
      </h2>
      <p className={styles.note}>{SKILLS_COPY.confidenceNote}</p>
      {day0 !== null && (
        <Row name={SKILLS_COPY.confidenceStart} value={day0} start />
      )}
      <ul className={styles.bars}>
        {ids.map((id) => (
          <li key={id}>
            <span className={styles.barLabel}>{CONFIDENCE_LABELS[id]}</span>
            {first?.[id] !== undefined && (
              <Row name={SKILLS_COPY.confidenceFirst} value={first[id] as number} start />
            )}
            {latest?.[id] !== undefined && <Row name={SKILLS_COPY.confidenceLatest} value={latest[id] as number} />}
          </li>
        ))}
      </ul>
    </section>
  );
}

function NextCard({ next }: { next: NonNullable<Skills["next"]> }) {
  const open = next.status === "available" || next.status === "in_progress";
  return (
    <section className={`${styles.card} ${styles.next}`} aria-labelledby="skills-next">
      <h2 className={styles.cardTitle} id="skills-next">
        {SKILLS_COPY.nextTitle}
      </h2>
      <p className={styles.line}>
        <strong>{next.title}</strong>
      </p>
      <p className={styles.note}>{next.reason}</p>
      {open ? (
        <Link className={styles.link} to={lessonRoute(next.lessonId)}>
          {SKILLS_COPY.nextOpen}
          <span className={styles.hidden}>{`: ${next.title}`}</span>
        </Link>
      ) : (
        next.unlockOn && <p className={styles.line}>{unlockLine(formatDate(next.unlockOn))}</p>
      )}
    </section>
  );
}

function Content({ data }: { data: Skills }) {
  const { skills, counts, confidence, next } = data;
  const hasActivity = skills.length > 0 || confidence.first !== null || Object.values(counts).some((n) => n > 0);
  return (
    <>
      {!hasActivity && (
        <p className={styles.empty} role="status">
          {SKILLS_COPY.empty}
        </p>
      )}
      {skills.map((skill) => (
        <section key={skill.id} className={styles.card} aria-labelledby={`skill-${skill.id}`}>
          <h2 className={styles.cardTitle} id={`skill-${skill.id}`}>
            {skill.label}
          </h2>
          {skill.roleplay && (
            <p className={styles.line}>
              {roleplayLine(
                skill.roleplay.runs,
                skill.roleplay.firstScore,
                skill.roleplay.latestScore,
                skill.roleplay.maxScore,
              )}
            </p>
          )}
          {skill.scenarios && <p className={styles.line}>{scenarioLine(skill.scenarios.practised, skill.scenarios.best)}</p>}
        </section>
      ))}
      <Confidence data={confidence} />
      {hasActivity && (
        <section className={styles.card} aria-labelledby="skills-counts">
          <h2 className={styles.cardTitle} id="skills-counts">
            {SKILLS_COPY.countsTitle}
          </h2>
          <dl className={styles.counts}>
            {(Object.keys(SKILLS_COUNT_LABELS) as (keyof typeof SKILLS_COUNT_LABELS)[]).map((key) => (
              <div key={key} className={styles.count}>
                <dt>{SKILLS_COUNT_LABELS[key]}</dt>
                <dd>{counts[key]}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}
      {next && <NextCard next={next} />}
      <p className={styles.note}>{SKILLS_COPY.limits}</p>
    </>
  );
}

export default function SkillsPage() {
  const request = useAppRequest((signal) => getSkills(signal), []);
  return (
    <div className={styles.page}>
      <Seo title={pageTitle(SKILLS_COPY.title)} description={SKILLS_COPY.subtitle} />
      <meta name="robots" content="noindex" />
      <h1 className={styles.title} data-app-heading tabIndex={-1}>
        {SKILLS_COPY.title}
      </h1>
      <p className={styles.subtitle}>{SKILLS_COPY.subtitle}</p>
      {request.status === "loading" && (
        <div className={styles.skeleton} role="status" aria-busy="true">
          <span className={styles.hidden}>{`Loading ${SKILLS_COPY.loading}`}</span>
        </div>
      )}
      {request.status === "error" && !request.handled && (
        <div className={styles.error} role="alert">
          <p>{APP_ERROR_MESSAGES[request.error.kind]}</p>
          <button type="button" className={styles.retry} onClick={request.retry}>
            {APP_COMMON.retry}
          </button>
        </div>
      )}
      {request.status === "ready" && <Content data={request.data} />}
    </div>
  );
}
