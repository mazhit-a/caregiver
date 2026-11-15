import { useParams } from "react-router";
import { getGuide, type Guide } from "../../api/guides";
import { useAppRequest } from "../../api/useAppRequest";
import { GUIDES_TEXT } from "../../content/app/guides";
import { Seo, pageTitle } from "../../layout/Seo";
import styles from "./GuidePage.module.css";

const telHref = (tel: string): string => `tel:${tel.replace(/[^\d+]/g, "")}`;

function Message({ title, body, onRetry }: { title: string; body: string; onRetry?: () => void }) {
  return (
    <div className={styles.message} role={onRetry ? "alert" : undefined}>
      <h1 className={styles.h1}>{title}</h1>
      <p className={styles.lead}>{body}</p>
      {onRetry ? (
        <button type="button" className={styles.retry} onClick={onRetry}>
          {GUIDES_TEXT.retry}
        </button>
      ) : null}
    </div>
  );
}

function Bullets({ id, title, items }: { id: string; title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <section className={styles.section} aria-labelledby={id}>
      <h2 id={id} className={styles.h2}>
        {title}
      </h2>
      <ul className={styles.bullets}>
        {items.map((t, i) => (
          <li key={i}>{t}</li>
        ))}
      </ul>
    </section>
  );
}

function GuideBody({ guide }: { guide: Guide }) {
  return (
    <>
      <Seo title={pageTitle(guide.title)} description={guide.summary} />
      <h1 className={styles.h1}>{guide.title}</h1>
      <p className={styles.lead}>{guide.summary}</p>
      {guide.callNow.length > 0 ? (
        <section className={styles.emergency} aria-labelledby="guide-call-now">
          <h2 id="guide-call-now" className={styles.emergencyTitle}>
            {guide.callNowTitle}
          </h2>
          <ul className={styles.bullets}>
            {guide.callNow.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </section>
      ) : null}
      <section className={styles.section} aria-labelledby="guide-steps">
        <h2 id="guide-steps" className={styles.h2}>
          {guide.stepsTitle}
        </h2>
        <ol className={styles.steps}>
          {guide.steps.map((s, i) => (
            <li key={i}>
              <strong className={styles.stepTitle}>{s.title}</strong>
              <span>{s.text}</span>
            </li>
          ))}
        </ol>
      </section>
      <Bullets id="guide-then" title={guide.thenTitle} items={guide.then} />
      <Bullets id="guide-dont" title={guide.dontTitle} items={guide.dont} />
      {guide.resources.length > 0 ? (
        <section className={styles.section} aria-labelledby="guide-help">
          <h2 id="guide-help" className={styles.h2}>
            {guide.resourcesTitle}
          </h2>
          <ul className={styles.resources}>
            {guide.resources.map((r) => (
              <li key={r.tel}>
                <a className={styles.call} href={telHref(r.tel)}>
                  <span>{r.label}</span>
                  <span className={styles.number}>{r.number}</span>
                </a>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {guide.sources.length > 0 ? (
        <section className={styles.sources} aria-labelledby="guide-sources">
          <h2 id="guide-sources" className={styles.h3}>
            {GUIDES_TEXT.sourcesTitle}
          </h2>
          <ul className={styles.sourceList}>
            {guide.sources.map((s) => (
              <li key={s.url}>
                <a href={s.url} target="_blank" rel="noopener noreferrer">
                  {s.name}
                </a>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <p className={styles.footer}>{guide.footer}</p>
    </>
  );
}

/** Public page: no session needed. One request: GET /api/guides/{id}. */
export default function GuidePage() {
  const { guideId = "" } = useParams();
  const request = useAppRequest((signal) => getGuide(guideId, signal), [guideId]);

  let content;
  if (request.status === "loading") {
    content = (
      <p className={styles.lead} role="status" aria-busy="true">
        {GUIDES_TEXT.loading}
      </p>
    );
  } else if (request.status === "error") {
    content =
      request.error.kind === "not_found" ? (
        <Message {...GUIDES_TEXT.notFound} />
      ) : (
        <Message {...GUIDES_TEXT.failed} onRetry={request.retry} />
      );
  } else {
    content = <GuideBody guide={request.data} />;
  }
  return <div className={styles.page}>{content}</div>;
}
