import { useAppCopy } from "../../../../api/AppDataProvider";
import type { ContentScreen as ContentData } from "../../../../api/appTypes";
import { DoSkip } from "../../../../components/lesson/DoSkip";
import { ExampleBubbles } from "../../../../components/lesson/ExampleBubbles";
import { ItemGrid } from "../../../../components/lesson/ItemGrid";
import { KeyIdea } from "../../../../components/lesson/KeyIdea";
import { OlliePose } from "../../../../components/lesson/OlliePose";
import { OllieTip } from "../../../../components/lesson/OllieTip";
import { PartLabel } from "../../../../components/lesson/PartLabel";
import { StepsList } from "../../../../components/lesson/StepsList";
import { StickyNote } from "../../../../components/lesson/StickyNote";
import { LESSON_COPY } from "../../../../content/app/lesson";
import type { ScreenProps } from "./types";
import styles from "./lessonScreens.module.css";

/** Optional blocks in a fixed order: body, image (beside the title), items, steps, do/skip, examples, note, key idea, tip. */
export function ContentScreen({ screen }: ScreenProps<ContentData>) {
  const labels = useAppCopy().data?.lesson.doSkip;
  return (
    <div className={styles["screen"]}>
      <PartLabel part={screen.part} />
      <div className={styles["titleRow"]}>
        <OlliePose pose={screen.image} />
        <h2 className={styles["title"]} data-screen-heading tabIndex={-1}>
          {screen.title}
        </h2>
      </div>
      {screen.body.map((paragraph) => (
        <p key={paragraph} className={styles["body"]}>
          {paragraph}
        </p>
      ))}
      {screen.items && screen.items.length > 0 && <ItemGrid items={screen.items} />}
      {screen.steps && screen.steps.length > 0 && <StepsList steps={screen.steps} />}
      {screen.dodont && labels && (
        <DoSkip
          doItems={screen.dodont.do}
          skipItems={screen.dodont.dont}
          doLabel={labels.doLabel}
          skipLabel={labels.skipLabel}
        />
      )}
      {screen.examples && screen.examples.length > 0 && <ExampleBubbles examples={screen.examples} />}
      {screen.note && <StickyNote line1={screen.note.line1} line2={screen.note.line2} />}
      {screen.keyIdea && <KeyIdea text={screen.keyIdea} />}
      {screen.tip && <OllieTip label={LESSON_COPY.ollieTip} text={screen.tip} />}
    </div>
  );
}
