import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../lib/api';

export interface Money { minor: number; currency: string; exponent: number }

export interface RecordOut {
  id: string;
  product: string;
  title: string;
  external_ref: string | null;
  status: string;
  value: Money | null;
  created_at: string;
}

export interface FactOut {
  key: string;
  value: unknown;
  confidence: number;
  display_state: 'high' | 'medium' | 'unknown';
  document_id: string;
  locator: string;
  char_start: number | null;
  char_end: number | null;
}

export function useRecords(product?: string) {
  return useQuery({
    queryKey: ['records', product ?? 'all'],
    queryFn: () =>
      api<RecordOut[]>(`/records${product ? `?product=${encodeURIComponent(product)}` : ''}`),
  });
}

export function useRecordFacts(recordId: string) {
  return useQuery({
    queryKey: ['facts', recordId],
    queryFn: () => api<FactOut[]>(`/records/${recordId}/facts`),
  });
}

export function useStartRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { record_id: string; agent: string }) =>
      api('/runs', { method: 'POST', body: JSON.stringify(vars) }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['runs'] }),
  });
}
