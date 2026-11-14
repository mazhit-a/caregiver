interface Props {
  /** Full title. Use pageTitle() for the "Page | Kelper" pattern. */
  title: string;
  description: string;
}

export function pageTitle(name: string): string {
  return `${name} | Kelper`;
}

/** React 19 hoists <title> and <meta> into <head>. */
export function Seo({ title, description }: Props) {
  return (
    <>
      <title>{title}</title>
      <meta name="description" content={description} />
    </>
  );
}
