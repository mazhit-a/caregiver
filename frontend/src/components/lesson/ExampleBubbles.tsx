import styles from "./lessonBlocks.module.css";

export function ExampleBubbles({ examples }: { examples: readonly { text: string; why: string }[] }) {
  return (
    <ul className={styles["examples"]}>
      {examples.map((example) => (
        <li key={example.text} className={styles["example"]}>
          <p className={styles["bubble"]}>{example.text}</p>
          <p className={styles["why"]}>{example.why}</p>
        </li>
      ))}
    </ul>
  );
}
