import styles from "./ImageFigure.module.css";

interface Props {
  src: string;
  /** Required. Pass "" only for purely decorative images. */
  alt: string;
  width: number;
  height: number;
  loading?: "eager" | "lazy";
  className?: string;
}

export function ImageFigure({ src, alt, width, height, loading = "lazy", className }: Props) {
  return (
    <img
      src={src}
      alt={alt}
      width={width}
      height={height}
      loading={loading}
      decoding="async"
      className={className ? `${styles.image} ${className}` : styles.image}
    />
  );
}
