import { EscalationCard, type EscalationOption } from '@bai/ui';

import { Empty, ErrorState, Loading } from '../components/States';
import { useEscalations, useResolveEscalation, type EscalationOut } from '../hooks/useEscalations';
import { ApiError } from '../lib/api';

/** Options describe their own consequence, so the user knows before clicking. */
function optionsFor(e: EscalationOut): EscalationOption[] {
  return e.options.map((label) => ({
    id: label,
    label,
    consequence: e.consequence === 'consequential' ? 'Acts on a live system' : 'Updates this record',
    reversible: e.reversible,
  }));
}

export function QueuePage() {
  const { data, isLoading, error, refetch } = useEscalations('open');
  const resolve = useResolveEscalation();

  if (isLoading) return <Loading what="the exception queue" />;

  if (error) {
    const e = error instanceof ApiError ? error : null;
    return (
      <ErrorState
        message={e?.message ?? 'We could not load the queue.'}
        next={e?.next}
        changed={e?.changed ?? false}
        requestId={e?.requestId}
        onRetry={() => void refetch()}
      />
    );
  }

  if (!data || data.length === 0) {
    return (
      <Empty
        title="Nothing needs you"
        body="Everything the agents handled went through without an exception. This is the state you want."
      />
    );
  }

  return (
    <main>
      <h1>Exception queue</h1>
      <p className="bai-muted">
        {data.length} {data.length === 1 ? 'item needs' : 'items need'} a decision.
      </p>

      {resolve.error instanceof ApiError && (
        <ErrorState
          message={resolve.error.message}
          next={resolve.error.next}
          changed={resolve.error.changed}
          requestId={resolve.error.requestId}
        />
      )}

      {data.map((e) => (
        <EscalationCard
          key={e.id}
          title={e.action_name}
          reason={e.reason}
          confidence={e.confidence ?? undefined}
          irreversible={e.consequence === 'consequential' && !e.reversible}
          options={optionsFor(e)}
          busy={resolve.isPending && resolve.variables.id === e.id}
          onResolve={(choice) => { resolve.mutate({ id: e.id, choice }); }}
        />
      ))}
    </main>
  );
}
