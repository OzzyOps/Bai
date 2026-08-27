import { supabase } from './supabase';

const BASE = (import.meta.env['VITE_API_BASE_URL'] as string | undefined) ?? 'http://localhost:8000';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
    /** Whether anything was actually changed. Surfaced to the user verbatim. */
    readonly changed: boolean,
    readonly next?: string,
    readonly requestId?: string,
  ) {
    super(message);
  }
}

/**
 * Call the API as the signed-in user.
 *
 * The session token goes to the API, which forwards it to Postgres, so every
 * query runs under that user's RLS policies. There is no privileged path.
 */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new ApiError('You are not signed in.', 'not_authenticated', 401, false);

  // HeadersInit may be a Headers instance or an array of pairs; spreading either
  // into an object literal yields numeric keys and silently drops the headers.
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`${BASE}${path}`, { ...init, headers });

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    throw new ApiError(
      (body['message'] as string | undefined) ?? 'Something failed. Nothing was changed.',
      (body['code'] as string | undefined) ?? 'unknown',
      res.status,
      (body['changed'] as boolean | undefined) ?? false,
      body['next'] as string | undefined,
      body['request_id'] as string | undefined,
    );
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}
