import { Confidence } from '../evidence/Confidence';
import { SourceCitation } from '../evidence/SourceCitation';

export interface EscalationOption {
  id: string;
  label: string;
  /** Shown before the click, not after. The user must know what they are choosing. */
  consequence: string;
  reversible: boolean;
}

export interface EscalationCardProps {
  title: string;
  reason: string;
  confidence?: number | undefined;
  irreversible: boolean;
  options: readonly EscalationOption[];
  evidence?: {
    documentId: string; filename: string; locator: string;
    charStart?: number | undefined; charEnd?: number | undefined;
  } | undefined;
  onResolve: (optionId: string) => void;
  busy?: boolean | undefined;
}

/**
 * The highest-stakes surface in any BAi product: the moment a person is asked
 * to decide.
 *
 * It states the decision, the evidence, the system's confidence, what each
 * option does, and whether it can be undone. It never leads with urgency, and
 * it never hides the irreversible option behind a friendlier default.
 */
export function EscalationCard({
  title, reason, confidence, irreversible, options, evidence, onResolve, busy = false,
}: EscalationCardProps) {
  return (
    <article className="bai-card bai-card--escalation" aria-busy={busy}>
      <header className="bai-card__head">
        <h3>{title}</h3>
        {confidence != null && <Confidence confidence={confidence} />}
      </header>

      <p className="bai-card__reason">{reason}</p>

      {evidence && (
        <div className="bai-evidence">
          <SourceCitation {...evidence} />
        </div>
      )}

      {irreversible && (
        <p className="bai-warning" role="note">
          This cannot be undone once done. It will always ask a person, whatever
          autonomy is granted.
        </p>
      )}

      <div className="bai-card__actions">
        {options.map((o) => (
          <button
            key={o.id}
            type="button"
            className="bai-btn"
            disabled={busy}
            onClick={() => { onResolve(o.id); }}
          >
            <span>{o.label}</span>
            <small>{o.consequence}{o.reversible ? '' : ' · cannot be undone'}</small>
          </button>
        ))}
      </div>
    </article>
  );
}
