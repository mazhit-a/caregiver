import type { IntroScreen as IntroData } from "../../../../api/appTypes";
import { OlliePose } from "../../../../components/lesson/OlliePose";
import { PartLabel } from "../../../../components/lesson/PartLabel";
import type { ScreenProps } from "./types";
import styles from "./lessonScreens.module.css";

export function IntroScreen({ screen }: ScreenProps<IntroData>) {
  return (
    <div className={styles["screen"]}>
      <PartLabel part={screen.part} />
      <div className={styles["titleRow"]}>
        <OlliePose pose={screen.image} />
        <h2 className={styles["title"]} data-screen-heading tabIndex={-1}>
          {screen.title}
        </h2>
      </div>
      <p className={styles["body"]}>{screen.body}</p>
      {screen.bullets.length > 0 && (
        <ul className={styles["bullets"]}>
          {screen.bullets.map((b) => (
            <li key={b}>
              <span className={styles["check"]} aria-hidden="true">
                ✓
              </span>
              <span>{b}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
