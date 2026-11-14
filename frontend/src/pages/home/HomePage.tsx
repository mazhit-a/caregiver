import { Link } from "react-router";
import { usePricing } from "../../api/usePricing";
import { CtaBand } from "../../components/marketing/CtaBand";
import { Faq } from "../../components/marketing/Faq";
import { FeatureRow } from "../../components/marketing/FeatureRow";
import { ImageFigure } from "../../components/marketing/ImageFigure";
import { NumberedSteps } from "../../components/marketing/NumberedSteps";
import { Section } from "../../components/marketing/Section";
import { StartLink } from "../../components/marketing/StartLink";
import { StatusBlock } from "../../components/StatusBlock";
import {
  HOME_CTA,
  HOME_FAQ,
  HOME_FEATURES,
  HOME_GAP,
  HOME_HERO,
  HOME_OLLIE,
  HOME_PRICING,
  HOME_SAFE,
  HOME_SEO,
  HOME_STEPS,
  fillTemplate,
} from "../../content/home";
import { Seo } from "../../layout/Seo";
import { ROUTES } from "../../routes";
import olliePointing from "../../assets/home/ollie-pointing.webp";
import ollieWaving from "../../assets/home/ollie-waving.webp";
import { HomePracticePreview } from "./HomePracticePreview";
import styles from "./HomePage.module.css";

function PricingTeaser() {
  const pricing = usePricing();
  if (pricing.status !== "ready") {
    return <StatusBlock status={pricing.status} what={HOME_PRICING.what} onRetry={pricing.retry} />;
  }
  const { currency, defaultPlanId, plans } = pricing.data;
  const plan = plans.find((p) => p.id === defaultPlanId) ?? plans[0];
  if (!plan) {
    return <StatusBlock status="error" what={HOME_PRICING.what} onRetry={pricing.retry} />;
  }
  const money = new Intl.NumberFormat("en-US", { style: "currency", currency });
  return (
    <div className={styles.priceText}>
      <h2 className={styles.priceTitle}>
        {fillTemplate(HOME_PRICING.headline, { price: money.format(plan.priceToday), period: plan.introPeriodText })}
      </h2>
      <p className={styles.priceDetail}>
        {fillTemplate(HOME_PRICING.detail, {
          renewal: money.format(plan.renewalPrice),
          renewPeriod: plan.renewPeriodText,
        })}
      </p>
    </div>
  );
}

function PracticeMock() {
  const m = HOME_FEATURES.practice.mock;
  return (
    <div className={styles.mockPractice} aria-hidden="true">
      <p className={styles.mockLabel}>{m.heading}</p>
      <div className={styles.scoreRow}>
        <div className={styles.scoreCard}>
          <p className={styles.scoreCaption}>{m.first.label}</p>
          <p className={styles.score}>{m.first.score}</p>
        </div>
        <div className={`${styles.scoreCard} ${styles.scoreCardLast}`}>
          <p className={styles.scoreCaption}>{m.last.label}</p>
          <p className={`${styles.score} ${styles.scoreLast}`}>{m.last.score}</p>
        </div>
      </div>
      <p className={styles.mockBody}>{m.best}</p>
    </div>
  );
}

function CourseMock() {
  const m = HOME_FEATURES.course.mock;
  const [first, second, third] = m.modules;
  if (!first || !second || !third) return null;
  return (
    <div className={styles.mockCourse} aria-hidden="true">
      <div className={`${styles.moduleRow} ${styles.moduleFirst}`}>
        <span className={styles.startHere}>{m.startHere}</span>
        <span className={styles.moduleName}>{first.name}</span>
        <span className={styles.moduleCount}>{first.lessons}</span>
      </div>
      <div className={`${styles.moduleRow} ${styles.moduleRule}`}>
        <span className={styles.moduleName}>{second.name}</span>
        <span className={styles.moduleCount}>{second.lessons}</span>
      </div>
      <p className={styles.why}>{m.why}</p>
      <div className={styles.moduleRow}>
        <span className={styles.moduleName}>{third.name}</span>
        <span className={styles.moduleCount}>{third.lessons}</span>
      </div>
    </div>
  );
}

function CardMock() {
  const m = HOME_FEATURES.tools.mock;
  return (
    <div className={styles.mockCard} aria-hidden="true">
      <p className={styles.scoreCaption}>{m.caption}</p>
      <p className={styles.cardTitle}>{m.title}</p>
      <p className={styles.cardLabel}>{m.calmsLabel}</p>
      <p className={`${styles.mockBody} ${styles.cardGap}`}>{m.calms}</p>
      <p className={styles.cardLabel}>{m.phrasesLabel}</p>
      <p className={styles.mockBody}>{m.phrases}</p>
    </div>
  );
}

function PlacesMock() {
  const [a, b, c] = HOME_FEATURES.places.cards;
  return (
    <div className={styles.places} aria-hidden="true">
      <div className={`${styles.place} ${styles.placeButter}`}>
        <p className={styles.placeTitle}>{a.title}</p>
        <p className={styles.placeText}>{a.text}</p>
      </div>
      <div className={`${styles.place} ${styles.placeIris}`}>
        <p className={styles.placeTitle}>{b.title}</p>
        <p className={styles.placeText}>{b.text}</p>
      </div>
      <div className={`${styles.place} ${styles.placeWhite}`}>
        <p className={styles.placeTitle}>{c.title}</p>
        <p className={styles.placeText}>{c.text}</p>
      </div>
    </div>
  );
}

export default function HomePage() {
  const f = HOME_FEATURES;
  return (
    <>
      <Seo title={HOME_SEO.title} description={HOME_SEO.description} />

      <Section>
        <div className={styles.hero}>
          <div className={styles.heroText}>
            <p className={styles.eyebrow}>{HOME_HERO.eyebrow}</p>
            <h1 className={styles.h1}>{HOME_HERO.title}</h1>
            <p className={styles.heroLead}>{HOME_HERO.lead}</p>
            <div className={styles.heroActions}>
              <StartLink />
              <span className={styles.note}>{HOME_HERO.note}</span>
            </div>
          </div>
          <div className={styles.heroPreview}>
            <HomePracticePreview />
          </div>
        </div>
      </Section>

      <Section variant="plum">
        <div className={styles.gap}>
          <p className={styles.gapStat}>{HOME_GAP.stat}</p>
          <p className={styles.gapText}>
            {HOME_GAP.text}
            <br />
            <span className={styles.gapSource}>{HOME_GAP.source}</span>
          </p>
        </div>
      </Section>

      <Section variant="butter">
        <div className={styles.ollie}>
          <ImageFigure
            src={ollieWaving}
            alt={HOME_OLLIE.imageAlt}
            width={473}
            height={640}
            className={styles.ollieImage}
          />
          <div className={styles.ollieText}>
            <h2 className={styles.h2}>{HOME_OLLIE.title}</h2>
            <p className={styles.quote}>{HOME_OLLIE.quote}</p>
            <p className={styles.small}>{HOME_OLLIE.text}</p>
          </div>
        </div>
      </Section>

      <Section>
        <div className={styles.steps}>
          <div className={styles.stepsHead}>
            <h2 className={styles.h2}>{HOME_STEPS.title}</h2>
            <Link to={ROUTES.how} className={styles.textLink}>
              {HOME_STEPS.link}
            </Link>
          </div>
          <NumberedSteps steps={HOME_STEPS.steps} columns={3} />
        </div>
      </Section>

      <Section>
        <div className={styles.features}>
          <FeatureRow title={f.practice.title} visual={<PracticeMock />}>
            <p className={styles.featureText}>{f.practice.text}</p>
            <Link to={ROUTES.practice} className={styles.textLink}>
              {f.practice.link}
            </Link>
          </FeatureRow>
          <FeatureRow title={f.course.title} visual={<CourseMock />} reverse>
            <p className={styles.featureText}>{f.course.text}</p>
            <Link to={ROUTES.course} className={styles.textLink}>
              {f.course.link}
            </Link>
          </FeatureRow>
          <FeatureRow title={f.tools.title} visual={<CardMock />}>
            <p className={styles.featureText}>{f.tools.text}</p>
            <Link to={ROUTES.tools} className={styles.textLink}>
              {f.tools.link}
            </Link>
          </FeatureRow>
          <FeatureRow title={f.places.title} visual={<PlacesMock />} reverse>
            <p className={styles.featureText}>{f.places.text}</p>
            <Link to={ROUTES.how} className={styles.textLink}>
              {f.places.link}
            </Link>
          </FeatureRow>
        </div>
      </Section>

      <Section variant="muted">
        <div className={styles.safe}>
          <h2 className={styles.h2}>{HOME_SAFE.title}</h2>
          <div className={styles.safeGrid}>
            {HOME_SAFE.cards.map((card) => (
              <div key={card.title} className={styles.safeCard}>
                <h3 className={styles.h3}>{card.title}</h3>
                <p className={styles.small}>{card.text}</p>
              </div>
            ))}
          </div>
        </div>
      </Section>

      <Section>
        <div className={styles.price}>
          <PricingTeaser />
          <Link to={ROUTES.pricing} className={styles.outline}>
            {HOME_PRICING.link}
          </Link>
        </div>
      </Section>

      <Section>
        <div className={styles.faq}>
          <h2 className={styles.faqTitle}>{HOME_FAQ.title}</h2>
          <Faq items={HOME_FAQ.items} />
        </div>
      </Section>

      <Section>
        <CtaBand
          title={HOME_CTA.title}
          text={HOME_CTA.text}
          visual={<ImageFigure src={olliePointing} alt={HOME_CTA.imageAlt} width={455} height={640} />}
        />
      </Section>
    </>
  );
}
