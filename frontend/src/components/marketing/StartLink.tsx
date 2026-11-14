import type { ReactNode } from "react";
import { Link } from "react-router";
import { ROUTES } from "../../routes";
import styles from "./StartLink.module.css";

interface Props {
  children?: ReactNode;
  onClick?: () => void;
}

/** Primary call to action: every "Get Mom's plan" goes to the quiz. */
export function StartLink({ children = "Get Mom’s plan", onClick }: Props) {
  return (
    <Link to={ROUTES.quiz} className={styles.start} onClick={onClick}>
      {children}
    </Link>
  );
}
