import { useParams } from "react-router";
import { getPublicCard } from "../../api/app";
import type { CardSnapshot } from "../../api/appTypes";
import { useAppRequest } from "../../api/useAppRequest";
import { PUBLIC_CARD, cardTitle, sharedBy, updatedOn } from "../../content/app/publicCard";
import { formatDate } from "../../format/date";
import { Seo } from "../../layout/Seo";
import styles from "./CardPage.module.css";

const tel = (phone: string): string => `tel:${phone.replace(/[^\d+]/g, "")}`;

function Chips({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <section className={styles.section} aria-labelledby={`card-${label}`}>
      <h2 id={`card-${label}`} className={styles.h2}>
        {label}
      </h2>
      <ul className={styles.chips}>
        {items.map((item, i) => (
          <li key={`${item}-${i}`} className={styles.chip}>
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}

function CardBody({ card }: { card: CardSnapshot }) {
  const S = PUBLIC_CARD.sections;
  return (
    <>
      <Seo title={`${cardTitle(card.displayName)} | Kelper`} description="A shared care card." />
      <h1 className={styles.h1}>{cardTitle(card.displayName)}</h1>
      <p className={styles.meta}>
        {updatedOn(formatDate(card.updatedOn, { year: true }))}
        {card.caregiverFirstName ? ` · ${sharedBy(card.caregiverFirstName)}` : ""}
      </p>
      <Chips label={S.enjoys} items={card.enjoys} />
      <Chips label={S.calms} items={card.calms} />
      <Chips label={S.avoid} items={card.avoid} />
      {card.rhythm ? (
        <section className={styles.section} aria-labelledby="card-rhythm">
          <h2 id="card-rhythm" className={styles.h2}>
            {S.rhythm}
          </h2>
          <p className={styles.text}>{card.rhythm}</p>
        </section>
      ) : null}
      {card.phrases.length > 0 ? (
        <section className={styles.section} aria-labelledby="card-phrases">
          <h2 id="card-phrases" className={styles.h2}>
            {S.phrases}
          </h2>
          <ul className={styles.list}>
            {card.phrases.map((p, i) => (
              <li key={`${p}-${i}`} className={styles.phrase}>
                {p}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {card.contacts.length > 0 ? (
        <section className={styles.section} aria-labelledby="card-contacts">
          <h2 id="card-contacts" className={styles.h2}>
            {S.contacts}
          </h2>
          <ul className={styles.list}>
            {card.contacts.map((c, i) => (
              <li key={`${c.name}-${i}`} className={styles.row}>
                <span className={styles.name}>
                  {c.name}
                  {c.role ? <span className={styles.role}> ({c.role})</span> : null}
                </span>
                {c.phone ? (
                  <a className={styles.call} href={tel(c.phone)}>
                    {c.phone}
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <section className={styles.section} aria-labelledby="card-helplines">
        <h2 id="card-helplines" className={styles.h2}>
          {S.helplines}
        </h2>
        <ul className={styles.list}>
          {card.helplines.map((h) => (
            <li key={h.name} className={styles.row}>
              <span className={styles.name}>{h.name}</span>
              <a className={styles.call} href={tel(h.phone)}>
                {h.phone}
              </a>
              <span className={styles.desc}>{h.description}</span>
            </li>
          ))}
        </ul>
      </section>
      <button type="button" className={styles.print} onClick={() => window.print()}>
        {PUBLIC_CARD.print}
      </button>
    </>
  );
}

function Message({ title, body, onRetry }: { title: string; body: string; onRetry?: () => void }) {
  return (
    <div className={styles.message} role={onRetry ? "alert" : undefined}>
      <h1 className={styles.h1}>{title}</h1>
      <p className={styles.text}>{body}</p>
      {onRetry ? (
        <button type="button" className={styles.print} onClick={onRetry}>
          {PUBLIC_CARD.retry}
        </button>
      ) : null}
    </div>
  );
}

/** Public page: no session, no token, no events. One request: GET /api/cards/{id}. */
export default function CardPage() {
  const { cardId = "" } = useParams();
  const request = useAppRequest((signal) => getPublicCard(cardId, signal), [cardId]);

  let content;
  if (request.status === "loading") {
    content = (
      <p className={styles.text} role="status" aria-busy="true">
        {PUBLIC_CARD.loading}
      </p>
    );
  } else if (request.status === "error") {
    const kind = request.error.kind;
    if (kind === "not_found") content = <Message {...PUBLIC_CARD.notFound} />;
    else if (kind === "gone") content = <Message {...PUBLIC_CARD.revoked} />;
    else if (kind === "rate_limited") content = <Message {...PUBLIC_CARD.rateLimited} onRetry={request.retry} />;
    else content = <Message {...PUBLIC_CARD.failed} onRetry={request.retry} />;
  } else {
    content = <CardBody card={request.data} />;
  }

  return (
    <main id="main" tabIndex={-1} className={styles.page}>
      <Seo title="Care card | Kelper" description="A shared care card." />
      {content}
    </main>
  );
}
