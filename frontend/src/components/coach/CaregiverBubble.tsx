import styles from "./coach.module.css";

export function CaregiverBubble({ text, label }: { text: string; label: string }) {
  return (
    <div className={styles["caregiver"]}>
      <span className={styles["bubbleLabel"]}>{label}</span>
      <p className={styles["caregiverBubble"]}>{text}</p>
    </div>
  );
}
