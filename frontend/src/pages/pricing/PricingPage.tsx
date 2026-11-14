import { usePricing } from "../../api/usePricing";
import { StatusBlock } from "../../components/StatusBlock";
import { Faq } from "../../components/marketing/Faq";
import { PageHero } from "../../components/marketing/PageHero";
import { Section } from "../../components/marketing/Section";
import { useCrisisList } from "../../layout/useCrisisList";
import { Seo } from "../../layout/Seo";
import {
  APS_LINE,
  BILLING_CARDS,
  BILLING_FAQ,
  BILLING_FAQ_TITLE,
  BILLING_TITLE,
  DONT_LIST,
  DO_LIST,
  HELP_TITLE,
  INCLUDED_ITEMS,
  INCLUDED_TITLE,
  PRICING_HERO,
  SAFETY_CARDS,
  SAFETY_TITLE,
  currencyItem,
} from "../../content/pricing";
import { PlanCard } from "./PlanCard";
import styles from "./PricingPage.module.css";

function telHref(phone: string): string {
  return `tel:${phone.replace(/[^\d+]/g, "")}`;
}

function Plans() {
  const pricing = usePricing();
  if (pricing.status !== "ready") {
    return <StatusBlock status={pricing.status} what="prices" onRetry={pricing.retry} />;
  }
  const { plans, currency } = pricing.data;
  return (
    <>
      <div className={styles.plans}>
        {plans.map((plan) => (
          <PlanCard key={plan.id} plan={plan} currency={currency} />
        ))}
      </div>
      <div className={styles.included}>
        <p className={styles.includedTitle}>{INCLUDED_TITLE}</p>
        <ul className={styles.includedList}>
          {[...INCLUDED_ITEMS, currencyItem(currency)].map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </>
  );
}

function CrisisSection() {
  const resources = useCrisisList();
  return (
    <Section labelledBy="pricing-help">
      <div className={styles.crisis}>
        <h2 id="pricing-help" className={styles.crisisTitle}>
          {HELP_TITLE}
        </h2>
        <ul className={styles.crisisLinks}>
          {resources.map((r, i) => (
            <li key={r.id}>
              <a
                href={telHref(r.phone)}
                className={i === 0 ? styles.crisisPrimary : styles.crisisLink}
              >
                {r.name}: {r.phone}
              </a>
            </li>
          ))}
        </ul>
        <p className={styles.crisisNote}>{APS_LINE}</p>
      </div>
    </Section>
  );
}

export default function PricingPage() {
  return (
    <>
      <Seo
        title="Pricing and safety | Kelper"
        description="Clear prices, how to cancel, and how Kelper keeps your information and your parent safe."
      />
      <PageHero title={PRICING_HERO.title} lead={PRICING_HERO.lead} />

      <Section labelledBy="pricing-plans">
        <h2 id="pricing-plans" className={styles.srOnly}>
          Plans
        </h2>
        <Plans />
      </Section>

      <Section variant="muted" labelledBy="pricing-billing">
        <h2 id="pricing-billing" className={styles.srOnly}>
          {BILLING_TITLE}
        </h2>
        <div className={styles.cards3}>
          {BILLING_CARDS.map((c) => (
            <div key={c.title} className={styles.note}>
              <h3 className={styles.noteTitle}>{c.title}</h3>
              <p className={styles.noteText}>{c.text}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section labelledBy="pricing-safety">
        <div className={styles.safety}>
          <h2 id="pricing-safety" className={styles.sectionTitle}>
            {SAFETY_TITLE}
          </h2>
          <div className={styles.doDont}>
            {[DO_LIST, DONT_LIST].map((list) => (
              <div key={list.title} className={styles.listCard}>
                <h3 className={styles.listTitle}>{list.title}</h3>
                <ul className={styles.list}>
                  {list.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className={styles.cards3}>
            {SAFETY_CARDS.map((c) => (
              <div key={c.title} className={styles.note}>
                <h3 className={styles.noteTitle}>{c.title}</h3>
                <p className={styles.noteText}>{c.text}</p>
              </div>
            ))}
          </div>
        </div>
      </Section>

      <CrisisSection />

      <Section labelledBy="pricing-faq">
        <div className={styles.faq}>
          <h2 id="pricing-faq" className={styles.sectionTitle}>
            {BILLING_FAQ_TITLE}
          </h2>
          <Faq items={BILLING_FAQ} />
        </div>
      </Section>
    </>
  );
}
