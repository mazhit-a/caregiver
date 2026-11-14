import type { PaywallPlanCopy } from "../../api/funnelTypes";
import styles from "./PaywallPage.module.css";

interface Props {
  plans: PaywallPlanCopy[];
  value: string;
  onChange: (planId: string) => void;
  legend: string;
}

/** Native radio group; every plan card has the same weight. Text is exactly what the API sent. */
export function PlanPicker({ plans, value, onChange, legend }: Props) {
  return (
    <fieldset className={styles.picker}>
      <legend className={styles.legend}>{legend}</legend>
      {plans.map((plan) => (
        // eslint-disable-next-line jsx-a11y/label-has-associated-control -- wraps the radio; text is in nested spans
        <label
          key={plan.id}
          className={`${styles.plan} ${plan.id === value ? styles.planOn : ""}`}
        >
          <input
            type="radio"
            name="plan"
            value={plan.id}
            checked={plan.id === value}
            onChange={() => onChange(plan.id)}
            className={styles.radio}
          />
          <span className={styles.planText}>
            <span className={styles.planLabel}>{plan.label}</span>
            <span className={styles.planPrice}>{plan.priceToday}</span>
            <span className={styles.planDetail}>{plan.detail}</span>
          </span>
        </label>
      ))}
    </fieldset>
  );
}
