import type { CardSnapshot } from "../../../api/appTypes";
import { CARE_CARD_TEXT } from "../../../content/app/careCard";
import { formatDate } from "../../../format/date";
import styles from "./careCard.module.css";

function Block({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h4>{title}</h4>
      {items.length === 0 ? (
        <p className={styles.muted}>{CARE_CARD_TEXT.nothingYet}</p>
      ) : (
        <ul>
          {items.map((item, i) => (
            <li key={`${item}-${i}`}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** The card as the link shows it: only the whitelisted snapshot fields, no quiz answers. */
export function CardPreview({ card }: { card: CardSnapshot }) {
  return (
    <article className={`${styles.card} ${styles.preview}`} aria-label={CARE_CARD_TEXT.previewTitle}>
      <h3>{card.displayName}</h3>
      <Block title={CARE_CARD_TEXT.enjoys} items={card.enjoys} />
      <Block title={CARE_CARD_TEXT.calms} items={card.calms} />
      <Block title={CARE_CARD_TEXT.avoid} items={card.avoid} />
      <div>
        <h4>{CARE_CARD_TEXT.rhythm}</h4>
        <p className={card.rhythm ? undefined : styles.muted}>{card.rhythm || CARE_CARD_TEXT.nothingYet}</p>
      </div>
      <Block title={CARE_CARD_TEXT.phrases} items={card.phrases} />
      <div>
        <h4>{CARE_CARD_TEXT.contacts}</h4>
        {card.contacts.length === 0 ? (
          <p className={styles.muted}>{CARE_CARD_TEXT.nothingYet}</p>
        ) : (
          <ul>
            {card.contacts.map((c, i) => (
              <li key={`${c.name}-${i}`}>
                {c.name}
                {c.role ? `, ${c.role}` : ""}: {c.phone}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <h4>{CARE_CARD_TEXT.helplines}</h4>
        <ul>
          {card.helplines.map((h) => (
            <li key={h.name}>
              {h.name}: {h.phone}
              <br />
              <span className={styles.helplineDesc}>{h.description}</span>
            </li>
          ))}
        </ul>
      </div>
      <p className={styles.hint}>
        {CARE_CARD_TEXT.updatedOn} {formatDate(card.updatedOn, { year: true })}
      </p>
    </article>
  );
}
