import type { ReactNode } from 'react';

/**
 * The four states every screen must cover, plus in-flight for agentic work.
 * Centralised so no screen can quietly ship with only the happy path.
 */

export function Loading({ what }: { what: string }) {
  return (
    <div className="bai-state" role="status" aria-live="polite">
      <span className="bai-spinner" aria-hidden="true" />
      <p>Loading {what}…</p>
    </div>
  );
}

export function InFlight({ what, onCancel }: { what: string; onCancel?: () => void }) {
  return (
    <div className="bai-state" role="status" aria-live="polite">
      <span className="bai-spinner" aria-hidden="true" />
      <p>{what}</p>
      {onCancel && (
        <button type="button" className="bai-btn" onClick={onCancel}>
          Stop
        </button>
      )}
    </div>
  );
}

export function Empty({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="bai-state bai-state--empty">
      <h2>{title}</h2>
      <p>{body}</p>
      {action}
    </div>
  );
}

/**
 * Error state. Says what happened, what it means, what to do — and whether
 * anything was changed, which is often the sentence that matters most.
 */
export function ErrorState({
  message, next, changed, requestId, onRetry,
}: {
  message: string;
  next?: string | undefined;
  changed: boolean;
  requestId?: string | undefined;
  onRetry?: (() => void) | undefined;
}) {
  return (
    <div className="bai-state bai-state--error" role="alert">
      <p>{message}</p>
      {!changed && <p className="bai-muted">Nothing was changed.</p>}
      {next && <p>{next}</p>}
      {onRetry && (
        <button type="button" className="bai-btn" onClick={onRetry}>
          Try again
        </button>
      )}
      {requestId && <p className="bai-cite">Request {requestId}</p>}
    </div>
  );
}
