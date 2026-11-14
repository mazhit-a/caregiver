import { NEED_HELP_NOW } from "../nav";

interface Props {
  className: string | undefined;
  onClick: () => void;
}

export function HelpButton({ className, onClick }: Props) {
  return (
    <button type="button" className={className} onClick={onClick}>
      {NEED_HELP_NOW}
    </button>
  );
}
