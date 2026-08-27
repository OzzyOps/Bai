import { Link } from 'react-router-dom';

import { Empty, ErrorState, Loading } from '../components/States';
import { useRecords } from '../hooks/useRecords';
import { useTenantFormat } from '../hooks/useTenantFormat';
import { ApiError } from '../lib/api';

export function RecordsPage() {
  const { data, isLoading, error, refetch } = useRecords();
  const fmt = useTenantFormat();

  if (isLoading) return <Loading what="records" />;

  if (error) {
    const e = error instanceof ApiError ? error : null;
    return (
      <ErrorState
        message={e?.message ?? 'We could not load your records.'}
        next={e?.next ?? 'Check your connection and try again.'}
        changed={e?.changed ?? false}
        requestId={e?.requestId}
        onRetry={() => void refetch()}
      />
    );
  }

  if (!data || data.length === 0) {
    return (
      <Empty
        title="No records yet"
        body="Records appear here once you create one or connect a system that feeds them in."
      />
    );
  }

  return (
    <main>
      <h1>Records</h1>
      <table>
        <caption className="bai-muted">
          Values are shown in each record&rsquo;s own currency, formatted for your
          organisation&rsquo;s locale.
        </caption>
        <thead>
          <tr>
            <th scope="col">Record</th>
            <th scope="col">Product</th>
            <th scope="col" data-numeric>Value</th>
            <th scope="col">Status</th>
            <th scope="col">Created</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r) => (
            <tr key={r.id}>
              <td>
                <Link to={`/records/${r.id}`}>{r.title}</Link>
                {r.external_ref && <span className="bai-cite">{r.external_ref}</span>}
              </td>
              <td>{r.product}</td>
              {/* Money is minor units + currency. Never a float, never assumed 2dp. */}
              <td data-money>{r.value ? fmt.money(r.value) : '—'}</td>
              <td>{r.status}</td>
              <td data-numeric>{fmt.date(r.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
