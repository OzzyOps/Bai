import { createClient } from '@supabase/supabase-js';

/**
 * The browser client uses the ANON key and nothing else.
 *
 * The anon key is designed to be public — RLS is what protects the data. The
 * service-role key bypasses RLS entirely and must never reach a browser; if you
 * find yourself wanting it here, the query belongs in a worker.
 */
/** Vite types every env entry as `any`; narrow it once, here, and nowhere else. */
function requiredEnv(name: string): string {
  const value: unknown = import.meta.env[name];
  if (typeof value !== 'string' || value === '') {
    throw new Error(`${name} must be set. Copy .env.example to .env and fill it in.`);
  }
  return value;
}

const url = requiredEnv('VITE_SUPABASE_URL');
const anonKey = requiredEnv('VITE_SUPABASE_ANON_KEY');

export const supabase = createClient(url, anonKey, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
});
