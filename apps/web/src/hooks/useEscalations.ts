import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../lib/api';

export interface EscalationOut {
  id: string;
  run_id: string;
  record_id: string | null;
  action_name: string;
  consequence: 'none' | 'reversible' | 'consequential';
  reversible: boolean;
  reason: string;
  confidence: number | null;
  options: string[];
  state: string;
  created_at: string;
}

export function useEscalations(state: 'open' | 'resolved' = 'open') {
  return useQuery({
    queryKey: ['escalations', state],
    queryFn: () => api<EscalationOut[]>(`/escalations?state=${state}`),
    // The exception queue is the working surface. Keep it fresh.
    refetchInterval: 30_000,
  });
}

export function useResolveEscalation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: string; choice: string; note?: string }) =>
      api<EscalationOut>(`/escalations/${vars.id}/resolve`, {
        method: 'POST',
        body: JSON.stringify({ choice: vars.choice, note: vars.note ?? null }),
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['escalations'] }),
  });
}
