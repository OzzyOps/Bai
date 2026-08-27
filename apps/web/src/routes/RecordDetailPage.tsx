import { useParams } from 'react-router-dom';
import { Confidence, SourceCitation } from '@bai/ui';

import { ErrorState, Loading } from '../components/States';
import { useRecordFacts } from '../hooks/useRecords';
import { ApiError } from '../lib/api';

export function RecordDetailPage() {
  const { id = '' } = useParams();
  const { data: facts, isLoading, error, refetch } = useRecordFacts(id);

  if (isLoading) return <Loading what="analysis" />;

  if (error) {
    const e = error instanceof ApiError ? error : null;
    return (
      <ErrorState
        message={e?.message ?? 'We could not load this analysis.'}
        next={e?.next}
        changed={e?.changed ?? false}
        requestId={e?.requestId}
        onRetry={() => void refetch()}
      />
    );
  }

  const certain = facts?.filter((f) => f.display_state !== 'unknown') ?? [];
  const uncertain = facts?.filter((f) => f.display_state === 'unknown') ?? [];

  return (
    <main>
      <h1>Analysis</h1>

      <section aria-labelledby="findings">
        <h2 id="findings">Findings</h2>
        {certain.map((f) => (
          <article key={f.key} className="bai-fact">
            <header>
              <h3>{f.key}</h3>
              <Confidence confidence={f.confidence} />
            </header>
            <p>{String(f.value)}</p>
            {/* Every fact carries its citation — there are no unattributed facts. */}
            <SourceCitation
              documentId={f.document_id}
              filename={f.document_id}
              locator={f.locator}
              charStart={f.char_start ?? undefined}
              charEnd={f.char_end ?? undefined}
            />
          </article>
        ))}
      </section>

      {uncertain.length > 0 && (
        <section aria-labelledby="unknown">
          {/* Rendered separately and labelled. An uncertain result must never sit
              among findings where it reads as one. */}
          <h2 id="unknown">Not determined</h2>
          <p className="bai-muted">
            We could not establish these with enough confidence to report them. They are
            listed so you can check them yourself, not as findings.
          </p>
          {uncertain.map((f) => (
            <article key={f.key} className="bai-fact bai-fact--unknown">
              <header>
                <h3>{f.key}</h3>
                <Confidence confidence={f.confidence} />
              </header>
              <SourceCitation
                documentId={f.document_id}
                filename={f.document_id}
                locator={f.locator}
                charStart={f.char_start ?? undefined}
                charEnd={f.char_end ?? undefined}
              />
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
