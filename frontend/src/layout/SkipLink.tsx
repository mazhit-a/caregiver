import styles from "./SkipLink.module.css";

export function SkipLink() {
  return (
    <a
      href="#main"
      className={styles.skip}
      onClick={(e) => {
        e.preventDefault();
        document.getElementById("main")?.focus();
      }}
    >
      Skip to main content
    </a>
  );
}
