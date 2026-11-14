import type { PricingPlan } from "../../api/types";
import { StartLink } from "../../components/marketing/StartLink";
import { introLine, renewLine } from "../../content/pricing";
import styles from "./PricingPage.module.css";

export function formatMoney(amount: number, currency: string): string {
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(amount);
  } catch {
    return amount.toFixed(2);
  }
}

interface Props {
  plan: PricingPlan;
  currency: string;
}

/** One plan, same weight as its neighbours: no badge, no highlight. */
export function PlanCard({ plan, currency }: Props) {
  const today = formatMoney(plan.priceToday, currency);
  const renewal = formatMoney(plan.renewalPrice, currency);
  return (
    <article className={styles.plan}>
      <h2 className={styles.planName}>{plan.label}</h2>
      <div>
        <p className={styles.price}>{today}</p>
        <p className={styles.priceNote}>{introLine(plan.introPeriodText)}</p>
      </div>
      <p className={styles.then}>
        <strong>
          Then {renewal} {renewLine(plan.renewPeriodText)}
        </strong>{" "}
        until you cancel.
      </p>
      <StartLink />
    </article>
  );
}
