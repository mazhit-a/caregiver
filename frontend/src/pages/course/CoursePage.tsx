import { CtaBand } from "../../components/marketing/CtaBand";
import { PageHero } from "../../components/marketing/PageHero";
import { Section } from "../../components/marketing/Section";
import {
  ALL_MODULES_TITLE,
  COURSE_CTA,
  COURSE_HERO,
  COURSE_MODULES,
  MODULE_ONE,
  ORDER_SECTION,
  QUICK_GUIDES,
} from "../../content/course";
import type { CourseModule } from "../../content/course";
import { Seo } from "../../layout/Seo";
import heroImage from "../../assets/course/ollie-reading.webp";
import styles from "./CoursePage.module.css";

function ModuleCard({ module }: { module: CourseModule }) {
  return (
    <li className={styles.card}>
      <div className={styles.cardHead}>
        <h3 className={styles.cardTitle}>{module.title}</h3>
        <span className={styles.count}>{module.count}</span>
      </div>
      {module.badge ? <span className={styles.soon}>{module.badge}</span> : null}
      <p className={styles.note}>{module.note}</p>
      <ul className={styles.cardLessons} aria-label={`Lessons in ${module.title}`}>
        {module.lessons.map((lesson) => (
          <li key={lesson.title}>{lesson.title}</li>
        ))}
      </ul>
    </li>
  );
}

export default function CoursePage() {
  return (
    <>
      <Seo
        title="The course | Kelper"
        description="See the modules and lessons in the Kelper course for family caregivers."
      />
      <PageHero
        title={COURSE_HERO.title}
        lead={COURSE_HERO.lead}
        image={{ src: heroImage, ...COURSE_HERO.image }}
      />

      <Section id="module-one" labelledBy="module-one-title">
        <div className={styles.moduleOne}>
          <div className={styles.stack}>
            <span className={styles.badge}>{MODULE_ONE.badge}</span>
            <h2 id="module-one-title" className={styles.h2}>
              {MODULE_ONE.title}
            </h2>
            <p className={styles.lead}>{MODULE_ONE.intro}</p>
            <p className={styles.why}>{MODULE_ONE.why}</p>
          </div>
          <ol className={styles.lessons} aria-label="Module 1 lessons">
            {MODULE_ONE.lessons.map((lesson, index) => (
              <li key={lesson.title} className={styles.lesson}>
                <span className={styles.lessonNumber} aria-hidden="true">
                  {index + 1}
                </span>
                <span className={styles.lessonTitle}>{lesson.title}</span>
                <span className={styles.minutes}>{lesson.minutes} min</span>
              </li>
            ))}
          </ol>
        </div>
      </Section>

      <Section id="order" labelledBy="order-title">
        <div className={styles.split}>
          <div className={styles.stack}>
            <h2 id="order-title" className={styles.h2}>
              {ORDER_SECTION.title}
            </h2>
            <p className={styles.lead}>{ORDER_SECTION.text}</p>
          </div>
          <ul className={styles.examples}>
            {ORDER_SECTION.examples.map((example) => (
              <li key={example.title} className={styles.example}>
                <p className={styles.exampleTitle}>{example.title}</p>
                <p className={styles.exampleWhy}>{example.why}</p>
              </li>
            ))}
          </ul>
        </div>
      </Section>

      <Section variant="muted" id="modules" labelledBy="modules-title">
        <div className={styles.modules}>
          <h2 id="modules-title" className={styles.h2}>
            {ALL_MODULES_TITLE}
          </h2>
          <ul className={styles.grid}>
            {COURSE_MODULES.map((module) => (
              <ModuleCard key={module.id} module={module} />
            ))}
          </ul>
        </div>
      </Section>

      <Section id="quick-guides" labelledBy="guides-title">
        <div className={styles.split}>
          <div className={styles.stack}>
            <h2 id="guides-title" className={styles.h2}>
              {QUICK_GUIDES.title}
            </h2>
            <p className={styles.lead}>{QUICK_GUIDES.text}</p>
          </div>
          <ul className={styles.guides}>
            {QUICK_GUIDES.items.map((guide) => (
              <li key={guide.id} className={styles.guide}>
                {guide.title}
              </li>
            ))}
          </ul>
        </div>
      </Section>

      <Section>
        <CtaBand title={COURSE_CTA.title} />
      </Section>
    </>
  );
}
