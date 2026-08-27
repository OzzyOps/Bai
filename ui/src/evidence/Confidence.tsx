import { displayState } from '@bai/tokens';

export interface ConfidenceProps {
  /** 0–1 as produced by the agent. */
  confidence: number;
  /** Rendered next to the badge for screen readers and sighted users alike. */
  label?: string;
}

const COPY = {
  high: 'High confidence',
  medium: 'Medium confidence',
  unknown: 'Not determined',
} as const;

/**
 * Confidence badge.
 *
 * Two rules this component exists to enforce:
 *  1. Low confidence renders as `unknown`, visually distinct from success. A
 *     grey result reads as "fine", and that is a trust failure.
 *  2. Colour is never the sole carrier of meaning — the state is always spelled
 *     out in text, not just implied by hue.
 */
export function Confidence({ confidence, label }: ConfidenceProps) {
  const state = displayState(confidence);
  const pct = Math.round(confidence * 100);

  return (
    <span className={`bai-chip bai-chip--${state}`} data-state={state}>
      <span aria-hidden="true" className="bai-chip__dot" />
      <span>{label ?? COPY[state]}</span>
      <span className="bai-tabular">{pct}%</span>
    </span>
  );
}
