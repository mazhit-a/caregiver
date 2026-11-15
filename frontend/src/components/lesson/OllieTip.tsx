import avatar from "../../assets/ollie-avatar.png";
import styles from "./lessonBlocks.module.css";

/** Ollie's line: avatar, a label and the text. `label` comes from the lesson copy. */
export function OllieTip({ label, text }: { label: string; text: string }) {
  return (
    <aside className={styles["tip"]}>
      <img className={styles["avatar"]} src={avatar} alt="" width={36} height={36} />
      <p className={styles["tipText"]}>
        <span className={styles["tipLabel"]}>{label}</span> {text}
      </p>
    </aside>
  );
}
