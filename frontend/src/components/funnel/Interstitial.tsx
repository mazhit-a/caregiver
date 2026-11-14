import ollie from "../../assets/funnel/ollie-thoughtful.webp";
import styles from "./Interstitial.module.css";

interface Props {
  title: string;
  body: string;
}

/** Reassurance card. The speaker from the API is ignored: the image is a fixed design choice. */
export function Interstitial({ title, body }: Props) {
  return (
    <div className={styles.card}>
      <img className={styles.image} src={ollie} alt="" width={150} height={229} />
      <h1 className={styles.title} data-funnel-heading tabIndex={-1}>
        {title}
      </h1>
      <p className={styles.body}>{body}</p>
    </div>
  );
}
