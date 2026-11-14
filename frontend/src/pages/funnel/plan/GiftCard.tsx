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
    <section className={styles.gift} aria-labelledby="gift-title">
      <h2 id="gift-title" className={styles.giftTitle}>
        {gift.status === "ready" ? gift.data.title : GIFT_CARD.title}
      </h2>
      {gift.status === "loading" && (
        <p role="status" className={styles.giftBody}>
          Getting your sheet…
        </p>
      )}
      {gift.status === "error" && (
        <div role="alert" className={styles.stack}>
          <p className={styles.giftBody}>We couldn't load your free sheet just now.</p>
          <button type="button" className={styles.secondary} onClick={gift.retry}>
            Try again
          </button>
        </div>
      )}
      {gift.status === "ready" && (
        <>
          <p className={styles.giftBody}>{gift.data.intro}</p>
          <Link to={ROUTES.gift} className={styles.secondaryLink}>
            {GIFT_CARD.cta}
          </Link>
          <p className={styles.small}>{GIFT_CARD.note}</p>
        </>
      )}
    </section>
  );
}
