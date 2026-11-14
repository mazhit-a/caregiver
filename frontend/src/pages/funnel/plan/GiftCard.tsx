import { Link } from "react-router";
import { getGift } from "../../../api/funnel";
import { useRequest } from "../../../api/useRequest";
import { GIFT_CARD } from "../../../content/funnel";
import { ROUTES } from "../../../routes";
import styles from "./plan.module.css";

/** Free sheet card. Its own request: a failure stays inside the card and never blocks the page. */
export function GiftCard() {
  const gift = useRequest((signal) => getGift(signal), []);
  return (
    <section className={styles.card} aria-labelledby="gift-title">
      <h2 id="gift-title" className={styles.h2}>
        {gift.status === "ready" ? gift.data.title : GIFT_CARD.title}
      </h2>
      {gift.status === "loading" && (
        <p role="status" className={styles.body}>
          Getting your sheet…
        </p>
      )}
      {gift.status === "error" && (
        <div role="alert" className={styles.stack}>
          <p className={styles.body}>We couldn't load your free sheet just now.</p>
          <button type="button" className={styles.secondary} onClick={gift.retry}>
            Try again
          </button>
        </div>
      )}
      {gift.status === "ready" && (
        <>
          <p className={styles.body}>{gift.data.intro}</p>
          <Link to={ROUTES.gift} className={styles.secondaryLink}>
            {GIFT_CARD.cta}
          </Link>
          <p className={styles.source}>{GIFT_CARD.note}</p>
        </>
      )}
    </section>
  );
}
