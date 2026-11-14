import styles from "./ActionBar.module.css";

interface Action {
  label: string;
  onClick: () => void;
}

interface Props {
  primary: Action & { disabled?: boolean };
  secondary?: Action;
}

/** Content for the FunnelScreen action bar. A disabled primary stays focusable (aria-disabled). */
export function ActionBar({ primary, secondary }: Props) {
  return (
    <>
      <button
        type="button"
        className={styles.primary}
        aria-disabled={primary.disabled || undefined}
        onClick={() => {
          if (!primary.disabled) primary.onClick();
        }}
      >
        {primary.label}
      </button>
      {secondary && (
        <button type="button" className={styles.secondary} onClick={secondary.onClick}>
          {secondary.label}
        </button>
      )}
    </>
  );
}
