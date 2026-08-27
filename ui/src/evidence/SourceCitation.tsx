export interface SourceCitationProps {
  documentId: string;
  filename: string;
  locator: string;
  charStart?: number | undefined;
  charEnd?: number | undefined;
  onOpen?: ((documentId: string, charStart?: number) => void) | undefined;
}

/**
 * The citation attached to every agent-produced fact.
 *
 * There is no unattributed fact in BAi — `Fact.__post_init__` refuses to
 * construct one — so this component has no "no source" branch by design.
 */
export function SourceCitation({
  documentId, filename, locator, charStart, charEnd, onOpen,
}: SourceCitationProps) {
  const span = charStart != null && charEnd != null ? ` · chars ${charStart}–${charEnd}` : '';
  const text = `${filename} · ${locator}${span}`;

  if (!onOpen) return <cite className="bai-cite">{text}</cite>;

  return (
    <button
      type="button"
      className="bai-cite bai-cite--link"
      onClick={() => { onOpen(documentId, charStart); }}
      aria-label={`Open ${filename} at ${locator}`}
    >
      {text}
    </button>
  );
}
