import styles from "./lessonBlocks.module.css";

export function ItemGrid({ items }: { items: readonly { title: string; text: string }[] }) {
  return (
    <ul className={styles["items"]}>
      {items.map((item) => (
        <li key={item.title} className={styles["item"]}>
          <span className={styles["itemTitle"]}>{item.title}</span>
          <span className={styles["itemText"]}>{item.text}</span>
        </li>
      ))}
    </ul>
  );
}
