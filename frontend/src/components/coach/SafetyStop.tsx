import { useEffect, useRef } from "react";
import styles from "./coach.module.css";

export interface SafetyResource {
  id: string;
  name: string;
  phone: string;
  description: string;
}

export interface SafetyLabels {
  title: string;
  body: string;
  leave: string;
  needHelp: string;
  keepPracticing: string;
  call: (name: string, phone: string) => string;
}

interface Props {
  kind: "crisis" | "emergency";
  resources: SafetyResource[];
  /** Server text for the emergency kind (with the 911 line). */
  emergencyText: string | null;
  labels: SafetyLabels;
  onLeave: () => void;
  onHelp?: () => void;
  /** Only emergency can continue; crisis ends the practice. */
  onContinue: () => void;
}

const telHref = (phone: string): string => `tel:${phone.replace(/[^\d+]/g, "")}`;

/** Replaces the practice input entirely. Names, numbers and descriptions come from the API. */
export function SafetyStop({ kind, resources, emergencyText, labels, onLeave, onHelp, onContinue }: Props) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), []);
  const only911 = resources.filter((r) => r.phone === "911");
  const list = kind === "emergency" && only911.length > 0 ? only911 : resources;

  return (
    <section className={styles["safety"]} aria-labelledby="coach-safety-title">
      <h2 id="coach-safety-title" className={styles["safetyTitle"]} ref={heading} tabIndex={-1}>
        {labels.title}
      </h2>
      <p className={styles["safetyBody"]}>{kind === "emergency" && emergencyText ? emergencyText : labels.body}</p>
      <ul className={styles["resources"]}>
        {list.map((r) => (
          <li key={r.id} className={styles["resource"]}>
            <a
              className={styles["call"]}
              href={telHref(r.phone)}
              aria-label={labels.call(r.name, r.phone)}
            >
              {r.name}: {r.phone}
            </a>
            <span className={styles["note"]}>{r.description}</span>
          </li>
        ))}
      </ul>
      <div className={styles["actions"]}>
        {kind === "emergency" && (
          <button type="button" className={styles["primary"]} onClick={onContinue}>
            {labels.keepPracticing}
          </button>
        )}
        <button type="button" className={styles["secondary"]} onClick={onLeave}>
          {labels.leave}
        </button>
        {onHelp && (
          <button type="button" className={styles["secondary"]} onClick={onHelp}>
            {labels.needHelp}
          </button>
        )}
      </div>
    </section>
  );
}
