import explaining from "../../assets/how/ollie-explaining.webp";
import reading from "../../assets/course/ollie-reading.webp";
import thinking from "../../assets/funnel/ollie-thoughtful.webp";
import note from "../../assets/tools/ollie-notebook.webp";
import styles from "./lessonBlocks.module.css";

/** Pose ids the lesson files use, mapped to the poses that exist as files. Others (calm, idea ...) draw nothing. */
const POSES: Readonly<Record<string, string>> = {
  "ollie-explaining": explaining,
  "ollie-reading": reading,
  "ollie-thinking": thinking,
  "ollie-note": note,
};

/** One decorative Ollie. An unknown pose id (or `ollie-calm-none`) renders nothing, never a stand-in. */
export function OlliePose({ pose }: { pose: string | null | undefined }) {
  const src = pose ? POSES[pose] : undefined;
  if (!src) return null;
  return <img className={styles["pose"]} src={src} alt="" width={96} height={96} loading="lazy" />;
}
